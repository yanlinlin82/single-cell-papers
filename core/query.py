import re

def tokenize(query):
    # 正则表达式用于识别引号中的字符串、括号、逻辑运算符和普通单词
    token_pattern = r'\"[^\"]+\"|\(|\)|AND|OR|NOT|[^()\s]+'
    tokens = re.findall(token_pattern, query)
    return tokens

def parse(tokens):
    def parse_expression(index):
        expr = []
        while index < len(tokens):
            token = tokens[index]

            if token == "(":
                # 递归处理括号中的表达式
                sub_expr, index = parse_expression(index + 1)
                expr.append(sub_expr)
            elif token == ")":
                # 括号闭合，返回当前表达式
                return expr, index
            elif token in {"AND", "OR", "NOT"}:
                expr.append(token)
            else:
                # 处理普通关键词和引号中的字符串
                if len(expr) > 0 and expr[-1] not in {"AND", "OR", "NOT", "("}:
                    # 在没有 AND/OR/NOT 的情况下，自动插入 AND
                    expr.append("AND")
                expr.append(token.strip('"'))  # 去除引号（如果有）
            index += 1
        return expr, index

    parsed_expr, _ = parse_expression(0)
    return parsed_expr

if __name__ == "__main__":
    # 示例
    query1 = 'next-generation sequencing'
    query2 = '"next-generation sequencing"'
    query3 = 'next-generation AND sequencing'

    tokens1 = tokenize(query1)
    parsed_query1 = parse(tokens1)

    tokens2 = tokenize(query2)
    parsed_query2 = parse(tokens2)

    tokens3 = tokenize(query3)
    parsed_query3 = parse(tokens3)

    print(f"Query 1: {parsed_query1}")
    print(f"Query 2: {parsed_query2}")
    print(f"Query 3: {parsed_query3}")

    query = 'next-generation AND (sequencing OR "targeted mutation analysis") AND NOT mutation'
    tokens = tokenize(query)
    parsed_query = parse(tokens)
    print(parsed_query)
