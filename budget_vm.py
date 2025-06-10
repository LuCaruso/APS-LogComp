import re

# --- EBNF ---
# <program>        ::= <month-decl> <setup-block> { <statement-body> } <report-stmt> ;
# <month-decl>     ::= "for" "month" <number> "/" <number> ;
# <setup-block>    ::= "setup" "{" { <var-stmt> | <budget-stmt> | <income-stmt> } "}" ;
# <statement-body> ::= <var-stmt> | <expense-stmt> ;
# <var-stmt>       ::= "var" <identifier> "=" <expr> ;
# <budget-stmt>    ::= "set" "budget" <identifier> "to" <expr> ;
# <income-stmt>    ::= "add" "income" <identifier> <expr> ;
# <expense-stmt>   ::= "spend" <expr> "on" <identifier> [ <recur-clause> ] ;
# <recur-clause>   ::= "every" "day" "for" <expr> "days" ;
# <report-stmt>    ::= "report" "month" <number> "/" <number> ;
# /* EXPRESSÕES ARITMÉTICAS */
# <expr>           ::= <term> { ("+" | "-") <term> } ;
# <term>           ::= <factor> { ("*" | "/") <factor> } ;
# <factor>         ::= <number> | <identifier> | "(" <expr> ")" ;
# /* IDENTIFICADORES */
# <identifier>     ::= <letter> { <letter> | <digit> | "_" } ;
# /* LITERAIS NUMÉRICOS */
# <number>         ::= <digit> { <digit> } ;


# --- Tokenização ---

TOKEN_SPEC = [
    ('NUMBER',      r'\d+'),
    ('ID',          r'[A-Za-z_][A-Za-z0-9_]*'),
    ('ASSIGN',      r'='),
    ('LBRACE',      r'\{'),
    ('RBRACE',      r'\}'),
    ('PLUS',        r'\+'),
    ('MINUS',       r'-'),
    ('MULT',        r'\*'),
    ('DIV',         r'/'),
    ('LPAREN',      r'\('),
    ('RPAREN',      r'\)'),
    ('NL',          r'\n'),
    ('SKIP',        r'[ \t]+'),
    ('COMMENT',     r'\#.*'),
    ('OTHER',       r'.'),
]

# Compila a regex para tokenização
TOKEN_REGEX = '|'.join('(?P<%s>%s)' % pair for pair in TOKEN_SPEC)

KEYWORDS = {
    'for', 'month', 'setup', 'var', 'set', 'budget', 'to', 'add', 'income',
    'spend', 'on', 'every', 'day', 'days', 'report'
}

class Token:
    def __init__(self, type_, value):
        self.type = type_
        self.value = value

    def __repr__(self):
        return f"Token({self.type!r}, {self.value!r})"

class Tokenizer:
    def __init__(self, text):
        self.tokens = []
        for mo in re.finditer(TOKEN_REGEX, text):
            kind = mo.lastgroup
            value = mo.group()
            if kind == 'NUMBER':
                self.tokens.append(Token('NUMBER', int(value)))
            elif kind == 'ID':
                if value in KEYWORDS:
                    # Keywords são tokens de seu próprio tipo (e.g., 'FOR', 'MONTH')
                    self.tokens.append(Token(value.upper(), value))
                else:
                    self.tokens.append(Token('ID', value))
            elif kind == 'SKIP' or kind == 'COMMENT':
                continue # Ignora espaços e comentários
            elif kind == 'NL':
                self.tokens.append(Token('NL', value))
            elif kind == 'OTHER':
                print(f"Warning: Unexpected character '{value}' ignored by tokenizer.")
                continue
            else:
                self.tokens.append(Token(kind, value))
        self.tokens.append(Token('EOF', None))
        self.pos = 0
        self.cur = self.tokens[0]

    def next(self):
        """Avança para o próximo token."""
        self.pos += 1
        if self.pos < len(self.tokens):
            self.cur = self.tokens[self.pos]
        else:
            self.cur = Token('EOF', None)

    def eat(self, ttype):
        """Consome o token atual se ele for do tipo esperado, e avança.
        Caso contrário, levanta um SyntaxError."""
        if self.cur.type == ttype:
            val = self.cur.value
            self.next()
            return val
        raise SyntaxError(f"Erro de sintaxe: Esperado '{ttype}', mas encontrado '{self.cur.type}' com valor '{self.cur.value}'")

# --- AST Nodes ---

class Node:
    """Classe base para todos os nós da Abstract Syntax Tree (AST)."""
    pass

class Program(Node):
    def __init__(self, month_year, setup_block, statements_body, report_stmt):
        self.month = month_year[0]
        self.year = month_year[1]
        self.setup_block = setup_block
        self.statements_body = statements_body
        self.report_stmt = report_stmt

    def evaluate(self, st):
        # Inicializa o estado com o mês e ano do programa
        st['month'] = self.month
        st['year'] = self.year

        # Avalia o bloco de setup
        self.setup_block.evaluate(st)

        # Avalia as instruções do corpo do programa
        for stmt in self.statements_body:
            stmt.evaluate(st)

        # Avalia a instrução de relatório final
        self.report_stmt.evaluate(st)


class Setup(Node):
    def __init__(self, items):
        self.items = items # Lista de VarDecl, BudgetDecl, IncomeDecl

    def evaluate(self, st):
        for item in self.items:
            item.evaluate(st)

class VarDecl(Node):
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr

    def evaluate(self, st):
        # Avalia a expressão e armazena o valor na tabela de símbolos 'vars'
        st['vars'][self.name] = self.expr.evaluate(st)

class BudgetDecl(Node):
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr

    def evaluate(self, st):
        # Avalia a expressão e armazena o valor na tabela de símbolos 'budgets'
        st['budgets'][self.name] = self.expr.evaluate(st)

class IncomeDecl(Node):
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr

    def evaluate(self, st):
        # Avalia a expressão, armazena o valor e o adiciona ao total de renda
        val = self.expr.evaluate(st)
        st['incomes'][self.name] = st['incomes'].get(self.name, 0) + val # Acumula se houver múltiplas entradas
        st['total_income'] += val

class Spend(Node):
    def __init__(self, expr, cat, recur_expr=None):
        self.expr = expr
        self.cat = cat
        self.recur_expr = recur_expr # Expressão para o número de dias em "every day for N days"

    def evaluate(self, st):
        amount_per_occurrence = self.expr.evaluate(st)
        
        if self.recur_expr:
            num_occurrences = self.recur_expr.evaluate(st)
            if not isinstance(num_occurrences, int) or num_occurrences < 0:
                raise ValueError(f"A expressão de recorrência deve resultar em um número inteiro não negativo, mas obteve: {num_occurrences}")
            
            total_amount = amount_per_occurrence * num_occurrences
            st['expenses'][self.cat] = st['expenses'].get(self.cat, 0) + total_amount
            st['total_expense'] += total_amount
        else:
            st['expenses'][self.cat] = st['expenses'].get(self.cat, 0) + amount_per_occurrence
            st['total_expense'] += amount_per_occurrence

class Report(Node):
    def __init__(self, month, year):
        self.month = month
        self.year = year

    def evaluate(self, st):
        # Verifica se o relatório é para o mês/ano do programa atual
        if st['month'] == self.month and st['year'] == self.year:
            print_report_html(st, self.month, self.year)
        else:
            print(f"Warning: Report requested for {self.month:02}/{self.year} but program is for {st['month']:02}/{st['year']}. Reporting anyway.")
            print_report_html(st, self.month, self.year)


# --- Expressões ---

class Number(Node):
    def __init__(self, value):
        self.value = value
    def evaluate(self, st):
        return self.value

class Ident(Node):
    def __init__(self, name):
        self.name = name
    def evaluate(self, st):
        # Tenta resolver o identificador como uma variável
        if self.name in st['vars']:
            return st['vars'][self.name]
        raise NameError(f"Variável não definida '{self.name}'")


class BinOp(Node):
    def __init__(self, op, left, right):
        self.op, self.left, self.right = op, left, right
    def evaluate(self, st):
        l = self.left.evaluate(st)
        r = self.right.evaluate(st)
        if self.op == '+': return l + r
        if self.op == '-': return l - r
        if self.op == '*': return l * r
        if self.op == '/':
            if r == 0:
                print("Erro de Execução: Divisão por zero. Retornando 0.")
                return 0
            return l // r


# --- Parser ---

class Parser:
    def __init__(self, tokenizer):
        self.tok = tokenizer

    def parse(self):
        # Ignora quebras de linha no início do arquivo
        self._skip_newlines()

        # <month-decl>
        month_year = self._parse_month_decl()
        self._skip_newlines()

        # <setup-block>
        setup_block_node = self._parse_setup_block()
        self._skip_newlines()

        # { <statement-body> }
        statements_body_nodes = []
        while self.tok.cur.type in ('VAR', 'SPEND'): # Verifica se é o início de um statement-body
            statements_body_nodes.append(self._parse_statement_body())
            self._skip_newlines()
        
        # <report-stmt> (OBRIGATÓRIO no final)
        report_stmt_node = self._parse_report_stmt()
        self._skip_newlines() # Pula quaisquer NLs após o report

        # Garante que não há mais tokens exceto EOF
        if self.tok.cur.type != 'EOF':
            raise SyntaxError(f"Erro de sintaxe: Tokens inesperados após o relatório: {self.tok.cur.type}")

        return Program(month_year, setup_block_node, statements_body_nodes, report_stmt_node)

    def _skip_newlines(self):
        """Pula todos os tokens NL consecutivos."""
        while self.tok.cur.type == 'NL':
            self.tok.next()

    def _parse_month_decl(self):
        self.tok.eat('FOR')
        self.tok.eat('MONTH')
        month = self.tok.eat('NUMBER')
        self.tok.eat('DIV')
        year = self.tok.eat('NUMBER')
        return month, year

    def _parse_setup_block(self):
        self.tok.eat('SETUP')
        self.tok.eat('LBRACE')
        items = []
        while True:
            self._skip_newlines()
            if self.tok.cur.type == 'RBRACE':
                self.tok.next()
                break # Fim do bloco setup
            
            # Escolhe o tipo de declaração dentro do setup
            if self.tok.cur.type == 'VAR':
                items.append(self._parse_var_decl())
            elif self.tok.cur.type == 'SET':
                items.append(self._parse_budget_decl())
            elif self.tok.cur.type == 'ADD':
                items.append(self._parse_income_decl())
            else:
                raise SyntaxError(f"Erro de sintaxe: Token inesperado no bloco setup: {self.tok.cur.type}")
        return Setup(items)

    def _parse_var_decl(self):
        self.tok.eat('VAR')
        name = self.tok.eat('ID')
        self.tok.eat('ASSIGN')
        expr = self._parse_expr()
        return VarDecl(name, expr)

    def _parse_budget_decl(self):
        self.tok.eat('SET')
        self.tok.eat('BUDGET')
        name = self.tok.eat('ID')
        self.tok.eat('TO')
        expr = self._parse_expr()
        return BudgetDecl(name, expr)

    def _parse_income_decl(self):
        self.tok.eat('ADD')
        self.tok.eat('INCOME')
        name = self.tok.eat('ID')
        expr = self._parse_expr()
        return IncomeDecl(name, expr)

    def _parse_statement_body(self):
        if self.tok.cur.type == 'VAR':
            return self._parse_var_decl()
        elif self.tok.cur.type == 'SPEND':
            return self._parse_spend_stmt()
        else:
            raise SyntaxError(f"Erro de sintaxe: Token inesperado no corpo da instrução: {self.tok.cur.type}. Esperado 'VAR' ou 'SPEND'.")

    def _parse_spend_stmt(self):
        self.tok.eat('SPEND')
        expr = self._parse_expr()
        self.tok.eat('ON')
        cat = self.tok.eat('ID')
        
        recur_expr = None
        if self.tok.cur.type == 'EVERY':
            self.tok.eat('EVERY')
            self.tok.eat('DAY')
            self.tok.eat('FOR')
            recur_expr = self._parse_expr()
            self.tok.eat('DAYS')
        return Spend(expr, cat, recur_expr)

    def _parse_report_stmt(self):
        self.tok.eat('REPORT')
        self.tok.eat('MONTH')
        month = self.tok.eat('NUMBER')
        self.tok.eat('DIV')
        year = self.tok.eat('NUMBER')
        return Report(month, year)

    # --- EXPRESSÕES (implementação de parser recursivo descendente) ---
    def _parse_expr(self):
        node = self._parse_term()
        while self.tok.cur.type in ('PLUS', 'MINUS'):
            op = self.tok.cur.value
            self.tok.next()
            node = BinOp(op, node, self._parse_term())
        return node

    def _parse_term(self):
        node = self._parse_factor()
        while self.tok.cur.type in ('MULT', 'DIV'):
            op = self.tok.cur.value 
            self.tok.next()
            node = BinOp(op, node, self._parse_factor())
        return node

    def _parse_factor(self):
        if self.tok.cur.type == 'NUMBER':
            val = self.tok.cur.value
            self.tok.next()
            return Number(val)
        elif self.tok.cur.type == 'ID':
            name = self.tok.cur.value
            self.tok.next()
            return Ident(name)
        elif self.tok.cur.type == 'LPAREN':
            self.tok.next() # Consome '('
            node = self._parse_expr()
            self.tok.eat('RPAREN') # Consome ')'
            return node
        else:
            raise SyntaxError(f"Erro de sintaxe: Token inesperado em fator: {self.tok.cur.type} com valor '{self.tok.cur.value}'")

# --- HTML Report Generation ---

def print_report_html(st, month, year):
    budgets = st['budgets']
    expenses = st['expenses']
    cats = sorted(set(budgets.keys()) | set(expenses.keys())) # Inclui categorias com ou sem orçamento/gasto

    html_output = []
    html_output.append(f"""<!DOCTYPE html>
<html><head><meta charset='utf-8'>
<title>Expense Report {month:02}/{year}</title>
<style>
    body {{ background: #f0f0f0; font-family: Arial, sans-serif; color: #333; margin: 0; padding: 0; }}
    .container {{ max-width: 800px; margin: 40px auto; background: #fff; padding: 20px;
                 box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-radius: 12px; }}
    h1 {{ text-align: center; margin-bottom: 20px; }}
    table {{ width: 100%; border-collapse: separate; border-spacing: 0;
            border-radius: 12px; overflow: hidden; margin-bottom: 20px; }}
    th {{ background: #223c53; color: #fff; padding: 12px; text-align: left; }}
    td {{ padding: 12px; border-bottom: 1px solid #ddd; }}
    tr:nth-child(even) td:not(.ok):not(.over) {{ background: #f9f9f9; }}
    td.ok   {{ background: #d4edda !important; color: #155724; }}
    td.over {{ background: #f8d7da !important; color: #721c24; }}
    .summary h2, .alerts h2 {{ text-align: left; margin-top: 40px; }}
    .summary p {{ line-height: 1.6; margin: 5px 0; }}
    .alerts ul {{ list-style: none; padding: 0; }}
    .alerts li {{ margin: 5px 0; padding: 10px; border-radius: 4px;
                  background: #f8d7da; color: #721c24; }}
</style>
</head><body>
<div class='container'>
    <h1>Expense Report for {month:02}/{year}</h1>
    <table>
        <tr><th>Category</th><th>Spent</th><th>Budget</th><th>Status</th></tr>""")
    
    for cat in cats:
        spent = expenses.get(cat, 0)
        budget = budgets.get(cat, 0)
        diff = spent - budget
        if diff > 0:
            status = f"OVER by {diff}"
            css = "over"
        else:
            status = "OK"
            css = "ok"
        html_output.append(f"        <tr><td>{cat}</td><td align='right'>{spent}</td><td align='right'>{budget}</td>"
                           f"<td class='{css}'>{status}</td></tr>")
    
    html_output.append(f"""    </table>
    <div class='summary'>
        <h2>Summary</h2>
        <p><strong>Total Income:</strong>   {st['total_income']}</p>
        <p><strong>Total Expense:</strong>  {st['total_expense']}</p>
        <p><strong>Net Balance:</strong>    {st['total_income'] - st['total_expense']}</p>
    </div>
    <div class='alerts'>
        <h2>Alerts</h2>
        <ul>""")
    
    for cat in cats:
        spent = expenses.get(cat, 0)
        budget = budgets.get(cat, 0)
        diff = spent - budget
        if diff > 0:
            html_output.append(f"            <li>{cat} exceeded budget by {diff}</li>")
    
    html_output.append("""        </ul>
    </div>
</div>
</body></html>""")

    print("\n".join(html_output)) # Imprime o HTML gerado

# --- Main Execution ---

def main():
    import sys
    if len(sys.argv) < 2:
        print("Uso: python budget_lang.py <caminho_do_arquivo.budget>")
        sys.exit(1)

    file_path = sys.argv[1]
    try:
        with open(file_path, 'r', encoding="utf-8") as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Erro: Arquivo '{file_path}' não encontrado.")
        sys.exit(1)
    except Exception as e:
        print(f"Erro ao ler o arquivo: {e}")
        sys.exit(1)

    try:
        tokenizer = Tokenizer(code)
        parser = Parser(tokenizer)
        prog = parser.parse()

        # Tabela de símbolos (estado do programa)
        st = {'vars': {}, 'budgets': {}, 'incomes': {}, 'expenses': {},
              'total_income': 0, 'total_expense': 0, 'month': None, 'year': None}
        
        prog.evaluate(st)

    except SyntaxError as e:
        print(f"Erro de Sintaxe: {e}")
        sys.exit(1)
    except NameError as e:
        print(f"Erro de Referência: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Erro de Valor: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Erro inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()