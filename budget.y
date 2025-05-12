%{
#include <stdio.h>
#include <stdlib.h>
#include "budget.tab.h"

extern int yylex(void);
void yyerror(const char *s) {
    fprintf(stderr, "Syntax Error: %s\n", s);
    exit(1);
}
%}

/* união de tipos */
%union {
    int   num;
    char *str;
}

/* tokens sem valor */
%token FOR MONTH SETUP VAR SET BUDGET TO ADD INCOME
%token SPEND EVERY DAY DAYS ON REPORT
%token LBRACE RBRACE EQUALS LPAREN RPAREN

/* tokens com valor */
%token <num>   NUMBER
%token <str>   IDENTIFIER

/* precedência (só p/ evitar conflitos) */
%left '+' '-'
%left '*' '/'

/* não-terminais com atributo <num> */
%type <num> expr recur_clause_opt

%%

program: month_decl setup_block stmt_list report_stmt
         { printf("Syntax OK\n"); }
         ;

month_decl: FOR MONTH NUMBER '/' NUMBER
            ;

setup_block: SETUP LBRACE setup_lines RBRACE
             ;

setup_lines: /* vazio */
           | setup_lines setup_line
           ;

setup_line: VAR IDENTIFIER EQUALS expr
          | SET BUDGET IDENTIFIER TO expr
          | ADD INCOME IDENTIFIER expr
          ;

stmt_list: /* vazio */
         | stmt_list statement
        ;

statement: VAR IDENTIFIER EQUALS expr
         | SPEND expr ON IDENTIFIER recur_clause_opt
         ;

report_stmt: REPORT MONTH NUMBER '/' NUMBER
           ;

/* recorrência opcional: every day for <expr> days */
recur_clause_opt: /* vazio */               
                { $$ = 0; }
                | EVERY DAY FOR expr DAYS  
                { $$ = $4; }
                ;

/* EXPRESSÕES ARITMÉTICAS — com ações explícitas em todas as alternativas */
expr: expr '+' expr      
    { $$ = 0; }
    | expr '-' expr      
    { $$ = 0; }
    | expr '*' expr      
    { $$ = 0; }
    | expr '/' expr      
    { $$ = 0; }
    | LPAREN expr RPAREN 
    { $$ = $2; }
    | NUMBER             
    { $$ = $1; }
    | IDENTIFIER         
    { $$ = 0; }       /* dummy */
    ;

%%

int main(void) {
    yyparse();
    return EXIT_SUCCESS;
}
