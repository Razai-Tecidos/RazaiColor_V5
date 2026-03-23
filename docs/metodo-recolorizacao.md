# Metodo de Recolorizacao Atual

## Objetivo

O metodo atual do projeto foi desenhado para recolorir tecidos claros preservando o aspecto fotografico do material.

O alvo nao e apenas trocar a cor. O alvo e manter:

- relevo
- dobras
- leitura luminosa do tecido
- profundidade nas sombras
- comportamento crivel das areas claras

## Estado Real do Metodo

O projeto ja possui um pipeline funcional em Lab.

Ele nao esta mais em fase apenas conceitual. O fluxo ativo ja roda em producao dentro do app e usa:

- conversao RGB para Lab
- mistura cromatica orientada por cor alvo
- preservacao estrutural do canal de luminancia
- protecao de sombras
- ajuste global de luminosidade
- retorno controlado para RGB com clipping e compressao de gamut simples

## Principio Central

O metodo trabalha com a separacao entre luz e cor.

No espaco Lab:

- `L` representa luminancia
- `a` representa o eixo verde <-> magenta
- `b` representa o eixo azul <-> amarelo

Essa separacao permite manter a estrutura luminosa do tecido enquanto os canais cromaticos sao empurrados na direcao da cor alvo.

## Pipeline Ativo

O fluxo atual do metodo e:

1. receber a imagem em RGB normalizado `[0.0, 1.0]`
2. converter a imagem para Lab
3. converter o hexadecimal alvo para Lab
4. manter uma copia do `L` original como base estrutural
5. calcular uma mascara de sombras a partir do `L`
6. aplicar a intensidade cromatica global nos canais `a` e `b`
7. reduzir a aplicacao de cor nas sombras profundas
8. calcular o deslocamento medio de luminancia em funcao da cor alvo
9. aplicar o ajuste global de luminosidade com protecao de sombras
10. subtrair um reforco de profundidade nas sombras para evitar aspecto chapado
11. limitar os canais Lab aos intervalos validos
12. converter o resultado de volta para RGB
13. aplicar compressao/clipping final em RGB

## Formula Geral do Metodo Atual

### Mistura cromatica

Os canais `a` e `b` sao movidos em direcao a cor alvo usando um peso global derivado de `color_strength`.

De forma simplificada:

$$
a_{new} = a_{orig} \cdot (1 - w) + a_{target} \cdot w
$$

$$
b_{new} = b_{orig} \cdot (1 - w) + b_{target} \cdot w
$$

onde `w` nao e completamente uniforme. Ele e atenuado nas sombras profundas.

### Mascara de sombra

A mascara de sombra e derivada do canal `L` normalizado.

No codigo atual, ela favorece a faixa escura e usa uma curva suavizada por potencia para evitar transicoes secas.

### Protecao cromatica nas sombras

Depois da mascara, a aplicacao da cor nas sombras recebe um redutor:

$$
shadow\_chroma\_application = 1 - (shadow\_mask \cdot shadow\_protection \cdot 0.58)
$$

Isso reduz o tingimento das regioes mais profundas, evitando o efeito de sombra lavada ou plastificada.

### Ajuste de luminancia

O app tambem permite que a imagem final se aproxime da luminancia media da cor alvo e receba um offset manual.

De forma simplificada:

$$
luminance\_delta = (mean(L_{target}) - mean(L_{original})) \cdot luminance\_strength
$$

$$
luminance\_adjustment = (luminance\_delta + lightness\_offset) \cdot luminance\_application
$$

com `luminance_application` reduzido nas sombras profundas.

### Reforco de profundidade nas sombras

Para evitar que a imagem perca volume nas regioes escuras, o pipeline subtrai um reforco adicional do `L` final:

$$
shadow\_depth\_boost = shadow\_mask \cdot shadow\_protection \cdot clamp(color\_strength / 3) \cdot 4
$$

Esse bloco foi introduzido para impedir que sombras fortes fiquem excessivamente coloridas e rasas.

## Sliders Ativos no App

O metodo exposto ao usuario hoje e controlado por quatro sliders:

### `color_strength`

- faixa: `0.0` a `3.0`
- padrao: `1.0`
- funcao: controla a forca da cor alvo nos canais `a/b`

Valores acima de `1.0` representam overshoot cromatico controlado.

### `luminance_strength`

- faixa: `0.0` a `1.0`
- padrao: `1.0`
- funcao: define o quanto a luminancia media da cor alvo influencia o resultado final

### `lightness_offset`

- faixa: `-40.0` a `40.0`
- padrao: `0.0`
- funcao: aplica um deslocamento global de luminosidade

### `shadow_protection`

- faixa: `0.0` a `1.0`
- padrao: `1.0`
- funcao: reduz a agressividade dos ajustes em sombras profundas

## O Que Esta Ativo e o Que Ainda Nao Esta

### Ativo hoje

- conversao RGB <-> Lab
- mistura cromatica em `a/b`
- overshoot de `color_strength` ate `3.0`
- mascara de sombras profunda
- ajuste medio de luminancia com protecao de sombras
- reforco de profundidade nas sombras
- compressao/clipping simples de gamut RGB
- live preview rapido em baixa resolucao
- geracao separada de imagem final em alta resolucao no momento da adicao a colecao

### Presente no codigo, mas nao integrado ao fluxo principal

- `prepare_luminance_channel` em [src/recolor/luminance.py](src/recolor/luminance.py)
- `build_highlight_mask` e `build_chroma_weight_map` em [src/recolor/masks.py](src/recolor/masks.py)
- `extract_texture_map` e `reinject_texture` em [src/recolor/texture.py](src/recolor/texture.py)

Esses modulos existem como base de evolucao, mas o pipeline ativo em [src/recolor/pipeline.py](src/recolor/pipeline.py) ainda opera no modo simples de preservacao do `L` com protecao de sombras.

## Escalas Numericas Usadas

- RGB de trabalho: `float32` em `[0.0, 1.0]`
- `L`: `float32` em `[0.0, 100.0]`
- `a/b`: `float32` em `[-128.0, 127.0]`

## Retorno para RGB

Depois do processamento em Lab, o resultado passa por:

1. clamp de intervalos validos em Lab
2. conversao para RGB
3. compressao opcional simples de gamut em torno do centro `0.5`
4. clipping final para `[0.0, 1.0]`

O debug exposto no app inclui:

- `clipped_ratio`
- `max_overflow`
- medias de peso, mascara e ajuste luminico

## Resultado Visual Esperado

Quando o metodo esta bem calibrado, o tecido deve:

- manter sombra crivel
- manter relevo e caimento
- absorver a cor alvo sem parecer pintado digitalmente
- preservar alguma delicadeza nas altas luzes

## Observacoes de Implementacao no App

Embora este documento trate do metodo de recolorizacao, o comportamento percebido pelo usuario hoje depende de duas resolucoes diferentes:

- o live preview usa imagem reduzida para velocidade
- a imagem adicionada a colecao e gerada em resolucao completa

Isso significa que o preview e uma aproximacao operacional rapida do resultado final, nao o mesmo buffer final usado no ZIP.

## Futuro Tecnico Relevante

Os proximos blocos tecnicos mais naturais para evolucao sao:

1. reativar e integrar highlight protection real no pipeline principal
2. expor controle dedicado para profundidade de sombra
3. integrar microtextura opcional com limite conservador
4. decidir se CLAHE leve deve ser um passo operacional real ou permanecer como modulo experimental
5. criar testes de regressao visual por imagem de referencia
