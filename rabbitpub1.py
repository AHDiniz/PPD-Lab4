import pika
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()
channel.queue_declare(queue='rsv/hello1')
channel.basic_publish(exchange='', routing_key='rsv/hello1', body='Hello World #1!')
print("Sent 'Hello World #1!'")
connection.close()