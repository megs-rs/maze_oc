# Caça ao Labirinto

Um jogo de labirinto 2D em visão superior feito com **Pygame** — usa imagens JPG para os carrinhos.

## Como Executar

```bash
python maze_chase.py
```

Requer Python 3 e Pygame (`pip install pygame`).

## Jogabilidade

- **Setas do teclado** para mudar a direção do seu carro — ele se move automaticamente pelo labirinto.
- **ESPAÇO** para atirar (pequeno intervalo entre tiros; balas param nas paredes).
- **Q** para sair a qualquer momento.

## Geração do Labirinto e Posição Inicial

- O jogador inicia na posição mais distante da saída (com ruído de ~15% para variação).
- BFS calcula todas as distâncias a partir da saída; tiles com distância ≥ 85% do máximo são candidatos.
- Se o candidato estiver perto de um inimigo, tenta outro tile do mesmo grupo.

## Pontuação

| Ação | Pontos |
|------|--------|
| Destruir inimigo segue-parede | 100 |
| Destruir inimigo médio | 200 |
| Destruir inimigo preciso | 300 |
| Completar fase (chegar à SAÍDA) | 500 × fase |

- **Recorde** salvo automaticamente entre sessões (arquivo `.highscore`).

## Inimigos

6 carros inimigos perseguem você pelo labirinto com diferentes IAs:

| Tipo          | Quant. | Comportamento                                                             |
|---------------|--------|---------------------------------------------------------------------------|
| Preciso       | 1      | Perseguição BFS com ruído baixo; alto viés ao jogador quando vagando     |
| Médio         | 2      | Perseguição BFS com ruído moderado; viés médio ao jogador quando vagando |
| Segue-parede  | 3      | Regra da mão direita — mantém parede à direita; só decide ao atingir o centro do tile |

- **Perseguição** ativa a ~550px+ do jogador; senão os inimigos **vagam**.
- Inimigos atingidos por balas reaparecem em outro local.
- Colidir com um inimigo custa 1 vida; reaparecimento com 3s de invulnerabilidade (pisca-pisca).

## Fases e Dificuldade

- Cada fase gera um novo labirinto com inimigos **mais rápidos e mais inteligentes**.
- Velocidade dos inimigos aumenta 15% por fase.
- Ruído diminui (inimigos acertam mais o caminho).
- Alcance de perseguição aumenta.
- Ao completar uma fase, a próxima começa automaticamente em 10 segundos com invulnerabilidade.
- **C** pula o countdown e avança para a próxima fase imediatamente.

## Vidas e Condição de Vitória

- **3 vidas** (exibidas como corações na tela).
- Alcance o **tile de saída** para completar a fase.
- 0 vidas → **FIM DE JOGO** (recorde mantido).
- Pressione **C** para avançar à próxima fase (vitória) ou **R** para reiniciar (derrota).

## Notas Técnicas

- Labirinto baseado em grid (17×17) gerado novamente a cada fase (sem semente fixa).
- Velocidade do jogador ~2,1 px/frame (sempre em movimento); inimigos ~1,0–1,8+ px/frame.
- IA inimiga usa BFS no grid + direcionamento em nível de pixel para o centro dos tiles.
- Implementação em arquivo único; dependências são Pygame e duas imagens JPG (jogador.jpg, inimigos.jpg).
