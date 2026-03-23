# RazaiColor V5

Aplicacao Streamlit para recolorizacao fotografica de tecidos claros, montagem de colecao visual e exportacao de pacote ZIP.

O projeto combina dois blocos principais:

- uma interface Streamlit orientada a operacao manual
- um pipeline de recolorizacao em Lab focado em preservar relevo, sombra e leitura fotografica do tecido

## Estado Atual

Hoje o sistema permite:

- upload de uma imagem base
- definicao manual de nome da cor e hexadecimal
- live preview rapido em baixa resolucao
- geracao da imagem final a partir dos sliders ativos
- adicao da imagem atual a uma colecao visual
- exibicao da colecao com thumbnails leves e paginacao
- recolher ou expandir a colecao para reduzir custo de renderizacao
- remocao de itens da colecao
- compressao manual apenas das imagens que ultrapassarem 2 MB
- liberacao imediata da etapa de preparo do ZIP quando toda a colecao ja estiver dentro do limite
- limpeza automatica da colecao ao trocar a imagem base por outra diferente

## Stack

- Python 3.14+
- Streamlit
- NumPy
- Pillow
- scikit-image

Dependencias declaradas em [requirements.txt](requirements.txt).

## Estrutura Principal

```text
app.py
src/
	recolor/
		__init__.py
		color_spaces.py
		gamut.py
		luminance.py
		masks.py
		models.py
		pipeline.py
		texture.py
docs/
	implementacao-tecnica.md
	manual-operacional.md
	metodo-recolorizacao.md
```

## Documentacao

- visao conceitual e tecnica do metodo atual: [docs/metodo-recolorizacao.md](docs/metodo-recolorizacao.md)
- arquitetura, estados e fluxo de implementacao real: [docs/implementacao-tecnica.md](docs/implementacao-tecnica.md)
- uso operacional da interface: [docs/manual-operacional.md](docs/manual-operacional.md)

## Como Executar

1. Instale as dependencias:

```bash
pip install -r requirements.txt
```

2. Inicie o app:

```bash
streamlit run app.py
```

## Fluxo Resumido

1. enviar imagem
2. informar nome e hex da cor
3. ajustar sliders
4. validar o live preview
5. adicionar a imagem atual a colecao
6. repetir para outras cores
7. abrir a colecao apenas quando quiser revisar os cards
8. comprimir apenas se houver imagens acima de 2 MB
9. preparar o ZIP quando a colecao estiver pronta
10. baixar o ZIP final

## Observacoes Importantes

- a colecao nao e comprimida no momento da adicao
- a compressao foi movida para uma etapa manual explicita, executada abaixo da colecao
- se todas as imagens ja estiverem abaixo de 2 MB, o preparo do ZIP fica liberado sem compressao adicional
- o live preview usa versao reduzida da imagem para manter resposta visual rapida
- a grade da colecao usa thumbnails para manter a interface responsiva
- a colecao pode ser recolhida para evitar rerenders pesados durante os ajustes
- o ZIP final e gerado sob demanda e fica em cache ate a colecao mudar
- os arquivos da colecao sao persistidos em uma pasta oculta do projeto, reduzindo o consumo de memoria em sessoes longas e evitando dependencia do diretorio temporario do sistema
