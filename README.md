# PPD-Lab4

Trabalho de Processamento Paralelo e Distribuído simulando uma blockchain.

## Instalação

Para rodar corretamente este projeto, instale as dependencias python contidas no arquivo [requirements.txt](./requirements.txt). Uma forma rápida de realizar essas instalações é rodar, caso esteja usando python, o comando:

`$ pip install -r ./requirements.txt`

ou, caso esteja usando python3, o comando:

`$ pip3 install -r ./requirements.txt`

Este projeto requer ainda a instalação do [RabbitMQ&trade;](https://www.rabbitmq.com/).

## Rodando

Para rodar este programa, primeiro esteja certo de ter o [RabbitMQ&trade;](https://www.rabbitmq.com/) instalado, para instalar é possível utilizar o script [inst.sh](./inst.sh) disponibilizado. Após isto, rode o cliente, caso esteja usando python, com o comando:

`$ python miner/main.py`

ou, caso esteja usando python3, o comando:

`$ python3 miner/main.py`

O sistema espera, atualmente que 10 processos identicos estejam rodando para continuar. Caso você esteja usando python3, pode rodar o script [run.sh](./run.sh):

`$ bash run.sh`

Caso você esteja usando python, pode modificar o script para rodar o comando python no lugar de python3.


## Mensagens e Exchanges Utilizados

Abaixo temos a descrição dos exchanges utilizados e das mensagens enviadas.

### Exchanges Declarados
| Exchange        | Descrição                      |
|:----------------|:---------------------------------|
| miner/init      | O cliente envia o seu id gerado localmente para conhecimento dos outros clientes. Todos os então clientes adicionam o id na sua cópia local. Todos os clientes reenviam a mensagem até que tenham todos os clientes na sua cópia local. |
| miner/election  | Cada um dos clientes envia o seu id e um número de voto para eleição do líder. Todos os clientes escolhem o cliente com maior voto e maior id para adicionar como líder. Todos os clientes reenviam o voto e sua mensagem de cliente enquanto não receber todos os votos. |
| miner/challenge | O Líder então gera e envia a transação, todos os clientes atualizam a lista local de transações com o objeto enviado e começam a tentar solucionar o mesmo com um número configurável de threads. |
| miner/solution  | O cliente que solucionar localmente envia a solução para todos os clientes. Todos os clientes então verificam a solução e esperam o resultado de miner/voting caso tenham concordado com a solução, caso contrário, continuam procurando a solução  |
| miner/voting    | Todos os clientes enviam o seu voto definido no subscribe da miner/solution. Ao receber todos os votos, cada cópia verifica se a maioria aceitou a solução, caso seja aceitado, o líder gera um novo desafio, caso contrário todos continuam procurando a solução da transação atual  |

### Mensagem e seus bodys

#### miner/init

| Propriedade | Tipo | Descrição                                      |
|:------------|:-----|:-----------------------------------------------|
| id          | int  | Id gerado pelo cliente que publicou a mensagem |


#### miner/election

| Propriedade | Tipo | Descrição                                                                                             |
|:------------|:-----|:------------------------------------------------------------------------------------------------------|
| id          | int  | Id gerado pelo cliente que publicou a mensagem identificando o seu voto                               |
| vote        | int  | Número gerado aleatoriamente pelo cliente que publicou a mensagem, identifica o seu voto para eleição |

#### miner/challenge

| Propriedade    | Tipo | Descrição                           |
|:---------------|:-----|:------------------------------------|
| transaction_id | int  | id da transação                     |
| challenge      | int  | Dificuldade do desafio              |
| generator_id   | int  | id do cliente que gerou a transação |

#### miner/solution

| Propriedade    | Tipo | Descrição                          |
|:---------------|:-----|:-----------------------------------|
| transaction_id | int  | id da transação                    |
| seed           | int  | Seed utilizada                     |
| client         | int  | id do cliente que enviou a solução |

#### miner/voting

| Propriedade    | Tipo | Descrição                          |
|:---------------|:-----|:-----------------------------------|
| voter          | int  | id do cliente enviando o voto      |
| valid          | int  | voto do cliente                    |
| transaction_id | int  | id da transação                    |
| seed           | int  | Seed utilizada                     |
| challenger     | int  | id do cliente que enviou a solução |


## Sobre o [RabbitMQ&trade;](https://www.rabbitmq.com/)

> With tens of thousands of users, RabbitMQ is one of the most popular open source message brokers. From T-Mobile to Runtastic, RabbitMQ is used worldwide at small startups and large enterprises.

> RabbitMQ is lightweight and easy to deploy on premises and in the cloud. It supports multiple messaging protocols. RabbitMQ can be deployed in distributed and federated configurations to meet high-scale, high-availability requirements.

> RabbitMQ runs on many operating systems and cloud environments, and provides a wide range of developer tools for most popular languages.

Texto retirado do site https://www.rabbitmq.com/. Acessado no dia 14/07/2022.
