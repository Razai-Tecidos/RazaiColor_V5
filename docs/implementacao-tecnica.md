# Implementacao Tecnica Atual

## Objetivo do Documento

Este documento descreve o estado real do projeto hoje.

Ele cobre:

- arquitetura do app
- fluxo operacional da interface
- estrutura dos modulos de recolorizacao
- estados de sessao importantes
- fluxo da colecao
- compressao e exportacao
- pontos de evolucao para o futuro

## Arquitetura do Projeto

### Camada de interface

- [app.py](app.py)

Responsabilidades principais:

- configurar o Streamlit
- manter estado de sessao
- ler upload de imagem
- renderizar os controles
- atualizar o live preview rapido
- gerar a imagem final para a colecao
- gerar thumbnails leves para exibicao dos cards
- gerenciar exclusao de itens
- controlar abertura e fechamento da colecao
- disparar a compressao manual para download apenas quando necessario
- montar e cachear o arquivo ZIP final
- gerar o ZIP apenas sob demanda para evitar reruns pesados em colecoes grandes
- persistir assets da colecao em uma pasta oculta do projeto para evitar crescimento excessivo da memoria da sessao

### Camada de recolorizacao

- [src/recolor/pipeline.py](src/recolor/pipeline.py)
- [src/recolor/models.py](src/recolor/models.py)
- [src/recolor/color_spaces.py](src/recolor/color_spaces.py)
- [src/recolor/gamut.py](src/recolor/gamut.py)

### Modulos auxiliares ainda nao conectados ao pipeline principal

- [src/recolor/luminance.py](src/recolor/luminance.py)
- [src/recolor/masks.py](src/recolor/masks.py)
- [src/recolor/texture.py](src/recolor/texture.py)

Esses modulos nao devem ser descritos como funcionalidades prontas do app. Eles existem no repositorio, mas ainda nao sao o caminho ativo da interface.

## Dependencias

Dependencias declaradas em [requirements.txt](requirements.txt):

- `numpy`
- `pillow`
- `scikit-image`
- `streamlit`

## Estruturas de Dados Principais

### `RecolorParams`

Definido em [src/recolor/models.py](src/recolor/models.py).

Campos relevantes para o fluxo atual:

- `target_hex`
- `color_strength`
- `luminance_strength`
- `lightness_offset`
- `shadow_protection`
- `gamut_compression`

Campos hoje presentes no modelo, mas nao usados pelo pipeline principal:

- `clahe_enabled`
- `clahe_clip_limit`
- `clahe_kernel_size`
- `highlight_protection`
- `texture_strength`
- `texture_blur_sigma`
- `texture_threshold`

### `RecolorResult`

Tambem definido em [src/recolor/models.py](src/recolor/models.py).

Retorna:

- `output_rgb`
- `output_lab`
- `prepared_l`
- `highlight_mask`
- `shadow_mask`
- `texture_map`
- `weight_map`
- `debug_info`

## Fluxo da Interface

### Etapa 1: upload

O usuario envia uma imagem em:

- `png`
- `jpg`
- `jpeg`
- `webp`

Ao confirmar o upload, o app move o usuario para a etapa de configuracao.

### Etapa 2: configuracao e recolorizacao

O usuario trabalha com:

- campo de nome da cor
- campo hexadecimal
- slider de saturacao/forca da cor
- slider de referencia de luminosidade
- slider de ajuste global de luz
- slider de protecao de sombras

O preview rapido e atualizado automaticamente a partir da imagem reduzida.

### Acao principal

O botao `Adicionar à Coleção` faz duas coisas:

1. gera a imagem final em alta resolucao com os sliders atuais
2. salva essa imagem na colecao

## Estado de Sessao Relevante

O app depende de `st.session_state` para sincronizar UI e processamento.

Chaves principais:

- `stage`
- `uploaded_image_bytes`
- `uploaded_image_name`
- `collection`
- `processed_preview_rgb`
- `processed_image_bytes`
- `recolor_params`
- `processing_debug`
- `live_preview_rgb`
- `live_preview_source_rgb`
- `live_preview_signature`
- `live_processing_debug`
- `color_strength_slider`
- `luminance_strength_slider`
- `lightness_offset_slider`
- `shadow_protection_slider`
- `collection_ready_for_download`
- `collection_page`
- `collection_page_size`
- `collection_zip_bytes`
- `collection_panel_expanded`

## Live Preview Rapido

O live preview usa uma copia reduzida da imagem original.

Fluxo:

1. a imagem original e convertida para RGB
2. e gerado um thumbnail com limite de lado maximo
3. o pipeline de recolorizacao roda sobre esse thumbnail
4. uma assinatura dos parametros evita recalculos redundantes

Vantagem:

- a interface responde muito mais rapido a sliders do que se recalculasse sempre a imagem full resolution

## Fluxo de Adicao a Colecao

Quando a imagem e adicionada, o item salvo inclui:

- `name`
- `hex`
- `image_name`
- `original_processed_image_path`
- `processed_image_path`
- `display_image_path`
- `processed_image_mime`
- `processed_image_extension`
- `compressed`
- `params`
- `debug`

Ponto importante:

- hoje nenhuma compressao acontece no momento da adicao
- a imagem entra na colecao como PNG final gerado pelo pipeline
- a UI da colecao passa a usar `display_image_path`, uma thumbnail leve separada do arquivo final de exportacao
- os arquivos finais e thumbnails deixam de viver apenas em memoria e passam a ser persistidos em uma pasta oculta do projeto

## Fluxo de Visualizacao da Colecao

Para reduzir travamentos em colecoes grandes, a grade da colecao foi separada da imagem final de exportacao.

Regras atuais:

- cada item armazena uma thumbnail dedicada para exibicao
- a grade renderiza no maximo uma pagina por vez
- a colecao pode permanecer recolhida
- quando recolhida, os cards nao sao renderizados
- adicionar um novo item nao reabre a colecao automaticamente
- os items da colecao sao migrados para armazenamento em disco, inclusive em sessoes antigas que ainda estejam abertas

Isso reduz:

- bytes enviados ao frontend em cada rerun
- quantidade de widgets ativos ao mesmo tempo
- interferencia da colecao sobre o live preview

## Fluxo de Exclusao

Cada item da colecao pode ser removido individualmente.

Ao excluir:

- o item e removido da lista em sessao
- o cache do ZIP e invalidado
- o estado `collection_ready_for_download` e recalculado

Isso impede que o ZIP antigo continue valido depois que a colecao mudou.

## Troca da Imagem Base

Quando o usuario volta para a tela de upload e seleciona uma imagem diferente:

- a colecao atual e limpa
- o painel da colecao volta ao estado recolhido
- o cache do ZIP e invalidado

Se o arquivo enviado for o mesmo, a colecao nao e descartada.

## Fluxo de Compressao para Download

O projeto separa explicitamente duas etapas:

### Colecao visual

- usada para revisao e comparacao das cores
- sem compressao obrigatoria no momento de adicionar

### Preparacao para download

- acionada manualmente por um botao abaixo da colecao
- processa apenas os itens acima de 2 MB
- mostra progresso
- atualiza `processed_image_path` de cada item
- atualiza `display_image_path` quando a imagem final muda
- define `compressed = True`
- recalcula a prontidao para download

Esse desenho foi adotado para evitar travar a experiencia de uso durante a montagem da colecao.

## Politica Atual de Compressao

O metodo de compressao atual tenta gerar PNG final na faixa alvo abaixo de 2 MB por imagem.

Regras do encoder atual:

- alvo maximo: `2 MB`
- alvo ideal: entre `1.8 MB` e `2.0 MB` quando possivel
- formato final priorizado: `PNG`
- estrategias usadas: quantizacao de cores, otimizacao e eventual downscale gradual

Importante:

- essa compressao so roda no botao de preparo para download
- ela nao participa do live preview
- ela nao participa da adicao simples a colecao
- se nenhum item ultrapassar 2 MB, nao ha compressao a executar

## Exportacao ZIP

O ZIP e gerado por [app.py](app.py) com:

- pasta `originals/` contendo a imagem base da colecao
- pasta `processed/` contendo as imagens prontas para exportacao
- `manifest.json` com metadados de cada item

O app usa um cache em sessao para os bytes do ZIP. Esse cache e invalidado sempre que a colecao muda, por exemplo:

- adicao de item
- exclusao de item
- troca da imagem base
- compressao de itens para download

O ZIP nao e mais montado automaticamente durante a renderizacao do botao de download.

Fluxo atual:

1. a colecao fica pronta para exportacao
2. o usuario clica em `Preparar ZIP para Download`
3. o app gera o arquivo uma unica vez
4. o botao real de download passa a usar o ZIP em cache

O botao de download so e habilitado quando:

- a colecao nao esta vazia
- `collection_ready_for_download == True`

Na pratica, isso significa:

- se toda a colecao ja estiver abaixo de 2 MB por item, a etapa de preparo do ZIP fica disponivel imediatamente
- se houver itens acima do limite, a compressao precisa ser executada antes do download

## Pipeline Tecnico de Recolorizacao

### Entrada

- imagem RGB em `float32` e faixa `[0.0, 1.0]`
- parametros em `RecolorParams`

### Etapas internas do pipeline atual

1. validar shape da imagem
2. clamp da entrada para `[0.0, 1.0]`
3. converter RGB para Lab
4. converter a cor alvo de hex para Lab
5. separar `L`, `a`, `b`
6. construir mascara de sombra
7. montar peso cromatico com base em `color_strength`
8. reduzir esse peso nas sombras profundas
9. misturar `a/b` com a cor alvo
10. calcular diferenca media de luminancia entre imagem e cor alvo
11. aplicar `luminance_strength` e `lightness_offset`
12. reduzir esse ajuste nas sombras
13. aplicar `shadow_depth_boost`
14. clamp dos canais Lab
15. converter Lab para RGB
16. aplicar compressao/clipping final de gamut
17. retornar imagem final e debug

## Debug e Diagnostico

O painel tecnico da interface hoje exibe metricas como:

- `clipped_ratio`
- `max_overflow`
- `mean_weight`
- `base_color_strength`
- `mean_luminance_application`
- `lightness_offset`
- `shadow_protection`
- `mean_shadow_depth_boost`

Essas metricas ajudam a entender por que uma configuracao ficou lavada, pesada ou excessivamente comprimida em gamut.

## Divergencia Entre Codigo e Modulos Auxiliares

O repositorio ainda contem modulos mais elaborados para:

- CLAHE em luminancia
- mascaras de highlight e shadow separadas
- extracao e reinjecao de textura

Hoje isso deve ser lido como base de evolucao, nao como descricao do fluxo em producao.

## Riscos Tecnicos Atuais

1. a compressao PNG pode ser custosa em imagens grandes
2. os modulos auxiliares ainda nao estao integrados e podem confundir manutencao se a documentacao ficar ambigua
3. parte dos campos do modelo ainda excede o que o pipeline realmente usa
4. o app ainda concentra preview, colecao e download na mesma tela, o que continua exigindo cuidado com rerenders

## Prioridades Naturais Para o Futuro

1. documentar testes visuais de regressao
2. decidir se preview, colecao e exportacao devem ser separados em etapas distintas
3. integrar highlight protection real no pipeline
4. transformar texture e CLAHE em features opcionais com validacao visual
5. mover a compressao para uma camada separada se o projeto crescer para lote ou backend
