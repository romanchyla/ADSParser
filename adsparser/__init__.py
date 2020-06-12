from lark import Lark, Transformer, v_args, Visitor
import re

grammar = Lark(r"""


    start: clause+ (operator clause)*
    clause: (modifier? ("(" clause (operator? clause)* ")")) 
        | query
    query: modifier? qterm
    modifier: PREPEND
    qterm: anyterm -> qterm | phrase | FORBIDDEN_LINE -> line
    PREPEND.2: /=/ | /\+/ | /\-/
    FORBIDDEN_LINE: /\[\w+\]/ | /\[\w+/ | /\w+\]/
    phrase: DOUBLE_QUOTED_STRING | SINGLE_QUOTED_STRING
    DOUBLE_QUOTED_STRING.3  : /"[^"]*"/ | /\+"[^"]*"/ | /\-"[^"]*"/
    SINGLE_QUOTED_STRING.3  : /'[^']*'/ | /\+'[^']*'/ | /\-'[^']*'/
    anyterm: /[^)^\]\[ \(\n\r]+/
    operator: OPERATOR | NEWLINE
    OPERATOR.2: "AND NOT " | "and not " | "and " | "AND " | "or " | "OR " | "not " | "NOT "  
    %import common.LETTER
    %import common.ESCAPED_STRING
    %import common.FLOAT
    %import common.DIGIT
    %import common.WS_INLINE
    %import common.NEWLINE
    %ignore WS_INLINE

    """, parser="lalr")


def parse_classic_keywords(query):
    """
    Wrapper function to parse the Classic keyword string and return a BBB-style keyword string

    :param query: string; Classic-style keyword query
    :return: string; BBB-style keyword query
    """
    # ignore underscores (to be used later as markers)
    clean_query = query.replace('_', ' ')
    
    # now deal with some ADS-classic query peculiarities that we
    # have actually found in the query profiles of ADS users

    # 1. newlines are treated as space (1727 instances)
    clean_query = clean_query.replace('\r\n', ' ')

    # 2. commas are simply used to separate keywords (274 instances)
    clean_query = clean_query.replace(',', ' ').replace(') (', ') OR (')

    # 3. a+b should be treated as "a +b" (165 instances)
    #    exception: "G79.29+0" 
    clean_query = re.sub(r'([a-zA-Z"])\+',r'\1 +', clean_query)

    # 4. 'a phrase' should be treated as "a phrase"
    #    exception: "Zel'dovich", "green's function"
    clean_query = re.sub(r"(\w)'(\w)", r"\1_\2", clean_query).replace("'", '"').replace('_', "'")
    
    tree = _parse_classic_keywords_to_tree(clean_query)

    v = TreeVisitor()
    new_query = v.visit(tree).output

    # finally, tweak output to fix edge cases
    
    # 1. (a OR -b) is rewritten as (a -b)
    new_query = new_query.replace(' OR -', ' -')

    # 2. a leading minus is ignored at the moment, so add a wildcard
    new_query = new_query.replace('(-', '(* -')
    if new_query.startswith('-'):
        new_query = '* ' + new_query
    
    return new_query


def _parse_classic_keywords_to_tree(data):
    """
    Given a string of keywords from Classic, parse the query tree

    :param data: string of Classic keywords
    :return: parsed tree
    """

    tree = grammar.parse(data)

    return tree


class TreeVisitor(Visitor):
    """
    Visitor class to transform the parsed tree into a BBB-style query.
    The final constructed query is stored in v.visit(tree).output
    """
    placeholder = 'PLACEHOLDER '

    def start(self, node):
        out = []
        newline = False
        for x in node.children:
            if hasattr(x, 'newline'):
                newline = True
            if hasattr(x, 'output'):
                out.append(getattr(x, 'output'))
            else:
                pass
        tmp = ' '.join(out)
        if newline:
            tmp = tmp.replace(self.placeholder, '')
        else:
            tmp = tmp.replace(self.placeholder, 'OR ')

        node.output = tmp

    def clause(self, node):
        out = []
        ops = ['AND', 'OR', 'NOT', 'AND NOT']
        prepend = ['=', '+', '-']
        for x in node.children:
            if x.data == 'modifier':
                continue
            if hasattr(x, 'output'):
                out.append(getattr(x, 'output'))
        output = []
        i = 0
        for o in out:
            if i == 0:
                output.append(o)
            else:
                if output[i-1].upper() in ops:
                    output.append(o)
                elif output[i-1] in prepend:
                    if i < 2:
                        output[i-1] += o
                    else:
                        output[i-1] = self.placeholder + output[i-1] + o
                    continue
                elif o.upper() in ops or o in prepend:
                    output.append(o.upper())
                else:
                    output.append(self.placeholder + o)
            i += 1

        if len(output) > 1:
            node.output = "({0})".format(' '.join(output))
        else:
            node.output = "{0}".format(' '.join(output))
        
        if node.children[0].data == 'modifier':
            node.output = node.children[0].output + node.output

    def query(self, node):
        node.output = ''.join([x.output for x in node.children])

    def qterm(self, node):
        node.output = node.children[0].output

    def anyterm(self, node):
        node.output = '{0}'.format(node.children[0].value.replace("'", "\'").replace('"', '\"').strip())

    def phrase(self, node):
        node.output = node.children[0].value.strip()

    def modifier(self, node):
        node.output = node.children[0].value.strip()

    def line(self, node):
        node.output = '{0}'.format(node.children[0].value.replace('[', '').replace(']', '').strip())

    def operator(self, node):
        v = node.children[0].value.upper()
        if v in ['\n', '\r', '\r\n']:
            node.newline = True
            v = 'OR'
        elif v.strip() not in ['AND', 'OR', 'NOT', 'AND NOT']:
            v = 'OR'
        else:
            v = v.strip()

        node.output = v
