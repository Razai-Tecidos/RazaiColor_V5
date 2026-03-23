# Manual Operacional

## Objetivo

Este documento explica como operar o app no estado atual, do upload ao ZIP final.

## Fluxo Completo

1. envie a imagem base
2. confirme o upload
3. informe nome da cor e hexadecimal
4. ajuste os sliders
5. acompanhe o live preview rapido
6. adicione a imagem atual a colecao
7. repita para outras cores
8. abra a colecao quando quiser revisar os cards
9. exclua itens se necessario
10. execute a compressao final somente se houver imagens acima de 2 MB
11. prepare o ZIP
12. baixe o ZIP

## Etapa 1: Upload

Formatos aceitos:

- `png`
- `jpg`
- `jpeg`
- `webp`

Ao clicar em `Confirmar upload`, o app entra na etapa de configuracao.

## Etapa 2: Definicao da Cor

Campos:

- `NOME`: nome operacional da cor
- `HEX`: codigo hexadecimal no formato `#RRGGBB`

Comportamento:

- editar o campo sozinho nao adiciona nada a colecao
- a adicao acontece apenas pelo botao `Adicionar à Coleção`

## Controles de Ajuste

### Saturacao / Forca da Cor

- controla a intensidade da cor alvo nos canais cromaticos
- pode passar de `1.0` ate `3.0`

### Referencia de Luminosidade

- puxa a luminancia media da imagem em direcao a cor alvo

### Ajuste Global de Luz

- escurece ou clareia o resultado final de forma global

### Protecao de Sombras

- reduz a agressividade dos ajustes em regioes escuras
- ajuda a manter relevo e profundidade

### Reset

Restaura os sliders para os valores padrao.

## Live Preview Rapido

O preview exibido ao lado dos sliders usa uma versao reduzida da imagem.

Isso existe para:

- responder rapido aos sliders
- evitar recalculo full resolution a cada microajuste

Importante:

- o live preview e uma aproximacao visual rapida
- a imagem adicionada a colecao e gerada em alta resolucao no momento da adicao

## Adicionar a Colecao

O botao `Adicionar à Coleção`:

1. gera a imagem final com os sliders atuais
2. salva essa imagem na colecao
3. salva tambem os metadados do item

Esse passo nao faz compressao para download.

## Colecao

A colecao agora pode ficar recolhida para manter a tela mais leve durante os ajustes.

Comportamento:

- use `Mostrar Coleção` para abrir os cards
- use `Ocultar Coleção` para recolher a grade
- quando recolhida, a interface evita renderizar todos os cards
- quando uma nova cor e adicionada, a colecao respeita o estado atual escolhido pelo usuario

Cada card da colecao mostra:

- imagem
- nome da cor
- hexadecimal
- tamanho atual do arquivo salvo no item
- botao `Excluir`

Observacao:

- a imagem mostrada no card e uma thumbnail otimizada para interface
- o arquivo real de exportacao permanece separado e continua sendo usado no ZIP
- a colecao agora usa uma pasta oculta do projeto para suportar sessoes maiores sem travar a memoria com dezenas de imagens

## Excluir Itens

Ao excluir um item:

- o card e removido
- o ZIP em cache deixa de valer
- a prontidao para download e recalculada

Se a colecao continuar toda dentro do limite de 2 MB por item, o download pode permanecer disponivel. Caso contrario, a compressao precisa ser executada novamente antes do download.

## Preparar Download

Existe um bloco especifico chamado `Preparo para Download`.

Ao clicar em `Comprimir Colecao para Download`:

1. apenas as imagens acima de 2 MB sao processadas
2. a barra de progresso avanca item a item
3. os arquivos finais para exportacao sao gerados
4. o ZIP e liberado

Se toda a colecao ja estiver abaixo do limite:

- nenhuma compressao adicional e necessaria
- o app informa que a colecao ja esta pronta para download

## Download do ZIP

O botao de download fica habilitado quando a colecao esta pronta para exportacao.

Isso pode acontecer de duas formas:

- depois da compressao final, se havia itens acima de 2 MB
- sem compressao adicional, se todos os itens ja estiverem dentro do limite

Antes do download real, o app agora pede uma acao intermediaria:

- clicar em `Preparar ZIP para Download`

Isso existe para evitar que colecoes grandes reconstruam o ZIP inteiro em reruns comuns da interface.

O ZIP inclui:

- imagens originais
- imagens processadas prontas para exportacao
- `manifest.json`

## Atalhos e Comportamentos Importantes

- editar nome e hex nao deve adicionar automaticamente
- a compressao final e separada da adicao para evitar travamento durante a montagem da colecao
- ao trocar a imagem base por uma imagem diferente, a colecao anterior e limpa automaticamente
- a colecao pode ficar recolhida para reduzir custo de renderizacao

## Solucao de Problemas

### O preview esta rapido, mas a adicao demora

Isso e esperado. A adicao gera a imagem final em alta resolucao.

### O ZIP esta desabilitado

Provavelmente existe ao menos uma imagem acima de 2 MB e falta executar a etapa `Comprimir Colecao para Download`.

### Exclui um item e o ZIP voltou a ficar indisponivel

Isso pode ser esperado. A colecao mudou e o app recalcula se ela ainda esta pronta para download.

### Mudei o hex e nada foi para a colecao

Isso e esperado. A adicao so acontece pelo botao.

### Troquei a imagem base e minha colecao sumiu

Isso e esperado quando a nova imagem enviada e diferente da anterior. A colecao pertence a imagem base atual.
