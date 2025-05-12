%option noyywrap
%{
#include "budget.tab.h"
#include <stdlib.h>
#include <string.h>
%}

/* Macros */
DIGIT      [0-9]
LETTER     [A-Za-z]
ID         {LETTER}({LETTER}|{DIGIT}|_)*
NUMBER     {DIGIT}+

%%

"#".*                    { /* ignora comentário */      }
[ \t\r\n]+              { /* ignora espaços e quebras */ }

"for"                    { return FOR;         }
"month"                  { return MONTH;       }
"setup"                  { return SETUP;       }
"{"                      { return LBRACE;      }
"}"                      { return RBRACE;      }
"var"                    { return VAR;         }
"="                      { return EQUALS;      }
"set"                    { return SET;         }
"budget"                 { return BUDGET;      }
"to"                     { return TO;          }
"add"                    { return ADD;         }
"income"                 { return INCOME;      }
"spend"                  { return SPEND;       }
"every"                  { return EVERY;       }
"day"                    { return DAY;         }
"days"                   { return DAYS;        }
"on"                     { return ON;          }
"report"                 { return REPORT;      }
"/"                      { return '/';         }
"("                      { return LPAREN;      }
")"                      { return RPAREN;      }
"+"                      { return '+';         }
"-"                      { return '-';         }
"*"                      { return '*';         }

{NUMBER}                 { yylval.num = atoi(yytext);    return NUMBER;    }
{ID}                     { yylval.str = strdup(yytext);  return IDENTIFIER;}

.                        { /* ignora qualquer outro */ }

%%
