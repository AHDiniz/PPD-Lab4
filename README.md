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

| Parâmetro | Tipo | Descrição |
|:----------|:---------------------|:---------------|
| App 1     | Description text 1.  | Requirements 1 |
| App 2     | Description text 2.  | None           |

## Sobre o [RabbitMQ&trade;](https://www.rabbitmq.com/)

> With tens of thousands of users, RabbitMQ is one of the most popular open source message brokers. From T-Mobile to Runtastic, RabbitMQ is used worldwide at small startups and large enterprises.

> RabbitMQ is lightweight and easy to deploy on premises and in the cloud. It supports multiple messaging protocols. RabbitMQ can be deployed in distributed and federated configurations to meet high-scale, high-availability requirements.

> RabbitMQ runs on many operating systems and cloud environments, and provides a wide range of developer tools for most popular languages.

Texto retirado do site https://www.rabbitmq.com/. Acessado no dia 14/07/2022.
