# Constitution — Inteligência Brasil

**Produto:** Inteligência Brasil  
**Tipo:** Produto de dados interno (B2B2C indireto)  
**Data:** 2026-06-23  
**Autor:** AI Builder Challenge — Seazone

---

## Por que este produto existe

A Seazone opera short-stay em dezenas de mercados brasileiros. Hoje, cada mercado novo
exige semanas de análise ad-hoc antes de uma decisão de entrada ou precificação. Esse
trabalho se repete, os resultados ficam em planilhas individuais, e o conhecimento não
escala. Inteligência Brasil existe para transformar esse trabalho recorrente em
inteligência de mercado contínua, acessível e auditável — para que qualquer analista
ou cliente possa responder "vale entrar nesse mercado?" em minutos, não semanas.

## O que o produto é — e o que não é

**É:**
- Uma camada analítica interna sobre dados de oferta (Airbnb/Booking scraping),
  demanda (ocupação estimada), e custo de mercado (portais de venda) para mercados
  brasileiros de short-stay
- A fonte de verdade única para KPIs de mercado: ADR, taxa de ocupação estimada, RevPAR,
  ROI por bairro × tipo de unidade
- Insumo direto para precificação (Seazone Price Engine) e para decisões de expansão
  de portfólio de clientes

**Não é:**
- Um sistema de precificação dinâmica (esse é o Price Engine, produto separado)
- Um portal público de dados de mercado (B2C)
- Um substituto para due diligence jurídica ou financeira de imóveis

## Princípios inegociáveis

1. **Rastreabilidade total:** cada número exposto deve ter linhagem até a fonte bruta
   (arquivo, data de captura, método de estimativa). Sem "número mágico" sem origem.

2. **Premissas explícitas como primeira classe:** onde há estimativa (ex: ocupação inferida
   por proxy de reviews), o produto exibe a premissa ao lado do número, não em nota de
   rodapé.

3. **Confiabilidade antes de cobertura:** mercados com amostra insuficiente (n < 30
   listings ativos) recebem flag de baixa confiança, nunca são silenciados, mas tampouco
   tratados como dado consolidado.

4. **Atualização incremental, não full-refresh:** o custo de re-processar todo o
   histórico diariamente é proibitivo. O design de pipeline deve ser incremental por
   padrão desde o dia 1.

5. **Orientado a decisão, não a exploração:** cada dashboard/endpoint entrega uma
   resposta para uma pergunta de negócio específica. Não é uma plataforma de BI genérico.
