from lark import Lark, Transformer, v_args, Visitor

grammar = Lark(r"""


    start: clause+ (operator clause)*

    clause: ("(" clause (operator? clause)* ")") 
        | query+

    query: qterm

    qterm: anyterm -> qterm | phrase | PREPEND -> prepend | FORBIDDEN_LINE -> line

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
    strip_operators = query.split('\r\n')
    if len(strip_operators) > 1:
        tmp = []
        for s in strip_operators:
            s = s.strip()
            if s.endswith('OR') or s.endswith('or'):
                s = s[:-2]
            if s.startswith('OR') or s.startswith('or'):
                s = s[2:]
            if s.endswith('AND') or s.endswith('and'):
                s = s[:-3]
            if s.startswith('AND') or s.startswith('and'):
                s = s[3:]
            tmp.append(s)
        query = '\r\n'.join(tmp)
    clean_query = query.replace(',', ' ').replace(') (', ') OR (').strip()
    tree = _parse_classic_keywords_to_tree(clean_query)

    v = TreeVisitor()
    new_query = v.visit(tree).output

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

    def query(self, node):
        node.output = node.children[0].output

    def qterm(self, node):
        node.output = node.children[0].output

    def anyterm(self, node):
        node.output = '{0}'.format(node.children[0].value.replace("'", "\'").replace('"', '\"').strip())

    def phrase(self, node):
        node.output = node.children[0].value.strip()

    def prepend(self, node):
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
