# Maze Chase

Um jogo de labirinto 2D em visão superior feito com **Pygame** — sem assets externos.

## Como Executar

```bash
python maze_chase.py
```

Requer Python 3 e Pygame (`pip install pygame`).

## Jogabilidade

- **Setas do teclado** para dirigir seu carro por um labirinto gerado proceduralmente (17×17).
- **ESPAÇO** para atirar (pequeno intervalo entre tiros; balas param nas paredes).
- **Q** para sair a qualquer momento.

## Inimigos

6 carros inimigos perseguem você pelo labirinto com diferentes IAs:

| Tipo          | Quant. | Comportamento                                                             |
|---------------|--------|---------------------------------------------------------------------------|
| Preciso       | 1      | Perseguição BFS com 5% de ruído; 50% de viés ao jogador quando vagando   |
| Médio         | 2      | Perseguição BFS com 30% de ruído; 25% de viés ao jogador quando vagando  |
| Segue-parede  | 3      | Travessia pela regra da mão direita — nunca usa BFS                       |

- **Perseguição** ativa a ~550px do jogador; senão os inimigos **vagam**.
- Inimigos atingidos por balas reaparecem em outro local.
- Colidir com um inimigo custa 1 vida; reaparecimento com ~1,5s de invulnerabilidade.

## Vidas & Condição de Vitória

- **3 vidas** (exibidas como corações na tela).
- Alcance o **tile de saída** para **VENCER**.
- 0 vidas → **GAME OVER**.
- Pressione **R** para reiniciar após vitória ou game over.

## Notas Técnicas

- Labirinto baseado em grid (17×17) gerado novamente a cada reinício (sem semente fixa).
- Velocidade do jogador ~2,5 px/frame; inimigos ~1,0–1,8 px/frame.
- IA inimiga usa BFS no grid + direcionamento em nível de pixel para o centro dos tiles.
- Implementação em arquivo único — única dependência é Pygame.
