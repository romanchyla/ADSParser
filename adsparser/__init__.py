from lark import Lark, Transformer, v_args, Visitor
import re

grammar = Lark(r"""


    start: clause+ (operator clause+)*

    clause: modifier? ("(" clause (operator? clause)* ")")
        | modifier? query

    query: qterm

    qterm: anyterm -> qterm | phrase | FORBIDDEN_LINE -> line

    modifier: PREPEND

    PREPEND.2: /=/ | /\+/ | /\-/

    FORBIDDEN_LINE: /\[\w+\]/ | /\[\w+/ | /\w+\]/

    phrase: DOUBLE_QUOTED_STRING | SINGLE_QUOTED_STRING | LATEX_QUOTED_STRING

    DOUBLE_QUOTED_STRING.3  : /"[^"]+"/
    SINGLE_QUOTED_STRING.3  : /'[^']+'/
    LATEX_QUOTED_STRING.3  : /``[^']+''/

    anyterm: /[^)\]\[ \(\n\r]+/

    operator: OPERATOR

    OPERATOR.2: "AND NOT " | "and not " | "OR NOT " | "or not " | "and " | "AND " | "or " | "OR " | "not " | "NOT "

    %import common.LETTER
    %import common.ESCAPED_STRING
    %import common.FLOAT
    %import common.DIGIT
    %import common.WS_INLINE

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
    clean_query = clean_query.replace('\r', ' ')
    clean_query = clean_query.replace('\n', ' ')

    # 2. commas are simply used to separate keywords (274 instances)
    clean_query = clean_query.replace(',', ' ').replace(') (', ') OR (')

    # 3. a+b should be treated as "a +b" (165 instances)
    #    exception: "G79.29+0"
    clean_query = re.sub(r'([a-zA-Z"])\+',r'\1 +', clean_query)

    # 4. a=b should be treated as "a =b"
    clean_query = re.sub(r'([a-zA-Z"])\=',r'\1 =', clean_query)

    # 5. a"b" should be treated as 'a "b"'
    #clean_query = re.sub(r'([a-zA-Z])"([^"]{2,})"([a-zA-Z])',r'\1 "\2" \3', clean_query)
    clean_query = re.sub(r'([a-zA-Z])"([^ ")]{1}[^"]+[^ "(]{1})"',r'\1 "\2"', clean_query)

    # 6. 'a phrase' should be treated as "a phrase"
    #    exception: "Zel'dovich", "green's function"
    clean_query = re.sub(r"(\w)'(\w)", r"\1_\2", clean_query).replace("'", '"').replace('_', "'")
    clean_query = re.sub(r'``([^"]+)""', r'"\1"', clean_query) # Correct latex quotes (i.e., ``term'') that we broken in the previous replace
    clean_query = re.sub(r'`([^"]+)"', r'"\1"', clean_query) # Correct bad latex quotes (i.e., not doubled: `term' which at this point will be `term")
    clean_query = re.sub(r'""([^"]+)""', r'"\1"', clean_query) # Correct bad double quotes (i.e., ''term'' which at this point will be ""term"")

    # 7. Isolated modifiers need to be pushed next to next term
    clean_query = clean_query.replace(' + ', ' +')
    clean_query = clean_query.replace(' - ', ' -')
    clean_query = clean_query.replace(' = ', ' =')
    clean_query = re.sub(r'^\+ ', '+', clean_query)
    clean_query = re.sub(r'^\- ', '-', clean_query)
    clean_query = re.sub(r'^= ', '=', clean_query)

    # 8. Correct bad modifiers order (e.g., =- => -=) and replace them since they are not accepted in modern ADS
    clean_query = clean_query.replace('=-', '-=')
    clean_query = clean_query.replace('=+', '+=')
    clean_query = clean_query.replace('+=', '=') # Priorize =
    clean_query = clean_query.replace('-=', '-') # Priorize -

    # 9. Remove modifiers at the end of a word or at the end of a sentence
    clean_query = re.sub(r'[\+\-=] ', r' ', clean_query)
    clean_query = re.sub(r'[\+\-=]$', r'', clean_query)

    # 10. Remove [] which lead to solr errors (e.g., forbidden lines)
    clean_query = clean_query.replace('[', '')
    clean_query = clean_query.replace(']', '')

    # 11. Remove unclosed parenthesis such as 'star (planet' or 'star) planet'
    #    (it will not catch '(star or planet) galaxy)' but there is only 1 case of these)
    clean_query = re.sub(r'\(([^)]*)$', r'\1', clean_query)
    clean_query = re.sub(r'^([^(]*)\)', r'\1', clean_query)

    # 12. Remove unwanted characters (e.g., &1536; or ;, # and $)
    clean_query = re.sub(r'&#\d+;', r' ', clean_query)
    clean_query = clean_query.replace(';', ' ').replace('#', '').replace('$', '')

    # 13. Remove unnecessary repeated modifiers (e.g., ++)
    clean_query = re.sub(r'[+]{2,}', r'+', clean_query)
    clean_query = re.sub(r'[-]{2,}', r'-', clean_query)
    clean_query = re.sub(r'[=]{2,}', r'=', clean_query)

    # 14. Remove unnecessary spaces (they can mess up things like 'AND   NOT')
    clean_query = re.sub(r'[ ]{2,}', r' ', clean_query)

    # 15. Remove any remaining spaces at the beginning/end of the query
    clean_query = clean_query.strip()

    if clean_query:
        tree = _parse_classic_keywords_to_tree(clean_query)

        v = TreeVisitor()
        new_query = v.visit(tree).output
        if new_query == "()":
            # It should be considered same as empty
            new_query = ""
    else:
        # Empty
        new_query = clean_query

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
    placeholder_or = 'PLACEHOLDER_OR '
    placeholder_and = 'PLACEHOLDER_AND '
    modifiers = {
        '=': placeholder_or,
        '+': placeholder_or,
        '-': placeholder_and,
    }

    def start(self, node):
        collected_output = self._collect_output(node.children)
        if len(collected_output) > 1 or (len(collected_output) == 1 and not (collected_output[0].startswith('(') and collected_output[0].endswith(')'))):
            # If multiple elements or one element not already in parenthesis,
            # wrap in parenthesis
            output = "(" + self._join(collected_output) + ")"
        else:
            output = self._join(collected_output)
        output = output.replace(self.placeholder_or, 'OR ')
        output = output.replace(self.placeholder_and, 'AND ')

        node.output = output

    def clause(self, node):
        collected_output = self._collect_output(node.children)
        if len(collected_output) > 0 and collected_output[0] in self.modifiers:
            # If collected outputs start with a modifier, add a proper placeholder in front
            # (e.g., ['+', 'exoplanet'])
            #         ^^^
            modifier = collected_output.pop(0)
            placeholder = self.modifiers[modifier]
            modifier = placeholder + modifier
        else:
            modifier = ''

        if len(collected_output) > 1:
            # If multiple elements, wrap in parenthesis
            node.output = modifier + "(" + self._join(collected_output) + ")"
        else:
            node.output = modifier + self._join(collected_output)

    def query(self, node):
        node.output = node.children[0].output

    def qterm(self, node):
        node.output = node.children[0].output

    def anyterm(self, node):
        operators = ("OR", "AND", "AND NOT", "OR NOT", "NOT")
        reserved_words = ("NEAR", )
        node.output = node.children[0].value.replace("'", "\'").replace('"', '\"').replace('"', "").replace('`', '').strip()
        if node.output.upper() in operators+reserved_words:
            node.output = '"'+node.output+'"'
        elif re.match(r'^\d{1,2}-\d{1,2}-\d{1,4}$', node.output):
            # Solr confuses this with dates
            node.output = '"'+node.output+'"'
        elif node.output.startswith('/'):
            node.output = node.output[1:]

    def phrase(self, node):
        # Transform all phrases to always use double quotes
        value = node.children[0].value.strip()
        if value.startswith("``"):
            value = re.sub("^``", '"', re.sub("''$", '"', value))
        elif value.startswith("'"):
            value = re.sub("^'", '"', re.sub("'$", '"', value))
        node.output = value.strip()

    def modifier(self, node):
        node.output = node.children[0].value.strip()

    def line(self, node):
        node.output = node.children[0].value.replace('[', '').replace(']', '').strip().encode('utf-8')

    def operator(self, node):
        v = node.children[0].value.upper()
        if v.strip() not in ['AND', 'OR', 'NOT', 'AND NOT']:
            v = 'OR'
        else:
            v = v.strip()

        node.output = v

    def _collect_output(self, node_children, start=False):
        """
        Concatenate output from all the children and apply the following rules:

        - If the first clause starts with a placeholder:
            - If the place holder is an 'OR' and it follows the modifier '-' (e.g., 'PLACEHOLDER_OR -'), it will add "* " in front
            - For the rest of cases, it will remove the placeholder
        - For clauses that are not the first one:
            - If the clause does not start with one already, add a placeholder
            - If the clause starts with a placeholder and the previous child was an operator, remove the placeholder (i.e., respect the already existing operator)

        Finally, it rearranges terms if there are substractions (e.g., -planet star => star AND -planet).
        """
        collected_output = []
        last_data_type = None
        first_clause = True
        for child in node_children:
            if hasattr(child, 'output'):
                output = child.output
                # Children will have data types:
                #   - 'clause'
                #   - 'query'
                #   - 'modifier'
                #   - 'operator'
                if child.data == "clause":
                    if first_clause:
                        first_clause = False
                        # Firt clause should not start with an operator
                        if output.startswith(self.placeholder_and):
                            if output[len(self.placeholder_and):].startswith("-"):
                                # PLACEHOLDER_AND -star => * PLACEHOLDER_AND -star
                                collected_output.append("*")
                            else:
                                # PLACEHOLDER_AND star => star
                                output = output[len(self.placeholder_and):]
                        elif output.startswith(self.placeholder_or):
                            # PLACEHOLDER_OR star => star
                            # PLACEHOLDER_OR +star => +star
                            output = output[len(self.placeholder_or):]
                    elif last_data_type not in ('operator', 'modifier') and not (output.startswith(self.placeholder_or)
                                or output.startswith(self.placeholder_and)):
                        # Append a placeholder if the clause does not start with one
                        # (i.e., single qterms) and it is not the first clause of
                        # the query (e.g., 'star exoplanet' => 'star PLACEHOLDER_OR exoplanet ')
                        collected_output.append(self.placeholder_or[:-1])
                    elif last_data_type == 'operator':
                        # If an operation was already in place, it takes precedent (i.e., ignore placeholder):
                        # (e.g., 'AND PLACEHOLDER_OR ' => 'AND ')
                        if output.startswith(self.placeholder_or):
                            output = output[len(self.placeholder_or):]
                        elif output.startswith(self.placeholder_and):
                            output = output[len(self.placeholder_and):]

                collected_output.append(output)
                last_data_type = child.data
            else:
                pass
        return self._sort(collected_output)

    def _sort(self, collected_output):
        """
        Rearrange statements so that if there are substractions (e.g., -term)
        they are moved to the end of the query while the rest is moved to the
        beginning and wrapped in parenthesis.
        (e.g., "star -planet hot" => "(star OR hot) AND -planet")

        """
        operators = (self.placeholder_or[:-1], self.placeholder_and[:-1], 'AND', 'OR', 'NOT', 'AND NOT', 'OR NOT',)
        substractions = []
        non_substractions = []
        previous_substracted = False
        for output in collected_output:
            if output.startswith("-") and len(non_substractions) > 0 and non_substractions[-1] in operators:
                # * AND -
                substractions.append(non_substractions.pop())
                substractions.append(output)
            elif output.startswith(self.placeholder_and + "-") or (output.startswith("-") and len(output) > 1):
                if len(non_substractions) > 0 and non_substractions[-1] == "*":
                    # * PLACEHOLDER_AND -
                    substractions.append(non_substractions.pop())
                    substractions.append(output)
                else:
                    # PLACEHOLDER_AND -
                    substractions.append(output)
                previous_substracted = True
            else:
                if previous_substracted and len(non_substractions) == 0 and output in operators:
                    # If there is an operator after, but we do not have any other term in the front, ignore it
                    # * Case where the operator and the term are separated in different elements
                    # PLACEHOLDER_AND -term1 OR term2
                    #                        ^^
                    pass # skip
                elif previous_substracted and len(non_substractions) == 0 and any([output.startswith(op+" ") for op in operators]):
                    # If there is an operator after, but we do not have any other term in the front, ignore it
                    # * Case where the operator and the term are merged together into the same string
                    # PLACEHOLDER_AND -term1 OR term2
                    #                        ^^^^^^^^
                    non_substractions.append(" ".join(output.split()[1:]))
                else:
                    non_substractions.append(output)
                previous_substracted = False
        if len(substractions) > 0 and len(non_substractions) > 0:
            if substractions[0] == "*":
                # 'term1 * PLACEHOLDER_AND -term2' => 'term1 PLACEHOLDER_AND -term2'
                substractions.pop(0)
            if len(non_substractions) > 1:
                collected_output = ["("] + non_substractions + [")"] + substractions
            else:
                collected_output = non_substractions + substractions
        return collected_output

    def _join(self, collected_output):
        """
        Concatenate collected output with spaces, except if it is a parenthesis
        or a modifier (e.g. ['star', 'AND', '-', 'planet'] => 'star AND -planet')
        """
        concatenated_output = ""
        for output in collected_output:
            if output in self.modifiers:
                concatenated_output += output
            elif output == '(':
                concatenated_output += output
            elif output == ')':
                concatenated_output = concatenated_output.strip() + output + " "
            else:
                concatenated_output += output + " "
        return concatenated_output.strip()

