import datetime
import hashlib
import json
from flask import Flask, jsonify, request
import requests
from uuid import uuid4
from urllib.parse import urlparse
import random

class Blockchain:
    def __init__(self):
        self.chain = []
        self.transactions = []
        self.players = []       
        self.vote = []          
        self.alive = []        
        self.killer = []
        self.create_block(proof = 1, prev_hash = '0')
        self.nodes = set()

    def create_block(self, proof, prev_hash):
        block = {'index': len(self.chain) + 1,
                 'timestamp': str(datetime.datetime.now()),
                 'proof': proof,
                 'prev_hash': prev_hash,
                 'transactions': self.transactions,
                 'players': list(self.players),
                 'vote': list(self.vote),
                 'alive': list(self.alive),
                 'killer': list(self.killer)}
        self.transactions = []
        self.chain.append(block)
        return block

    def get_prev_block(self):
        return self.chain[-1]

    def proof_of_work(self, prev_proof):
        new_proof = 1
        check_proof = False
        while not check_proof:
            hash_operation = hashlib.sha256(str(new_proof**2 - prev_proof**2).encode()).hexdigest()
            if hash_operation[:4] == '0000':
                check_proof = True
            else:
                new_proof += 1
        return new_proof

    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def is_chain_valid(self, chain):
        prev_block = chain[0]
        block_index = 1
        while block_index < len(chain):
            block = chain[block_index]
            if block['prev_hash'] != self.hash(prev_block):
                return False
            prev_proof = prev_block['proof']
            proof = block['proof']
            hash_operation = hashlib.sha256(str(proof**2 - prev_proof**2).encode()).hexdigest()
            if hash_operation[:4] != '0000':
                return False
            prev_block = block
            block_index += 1
        return True

    def add_transaction(self, sender, receiver, amount):
        self.transactions.append({'sender': sender,
                                  'receiver': receiver,
                                  'amount': amount})
        prev_block = self.get_prev_block()
        return prev_block['index'] + 1

    def add_player(self, player_name):
        self.players.append(player_name)
        self.alive.append(1)
        self.vote.append(1)
        prev_block = self.get_prev_block()
        return prev_block['index'] + 1

    def add_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def replace_chain(self):
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)
        for node in network:
            response = requests.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                if length > max_length and self.is_chain_valid(chain):
                    max_length = length
                    longest_chain = chain
        if longest_chain:
            self.chain = longest_chain
            return True
        return False

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

node_address = str(uuid4()).replace('-', '')

blockchain = Blockchain()

@app.route('/mine_block', methods=['GET'])
def mine_block():
    prev_block = blockchain.get_prev_block()
    prev_proof = prev_block['proof']
    proof = blockchain.proof_of_work(prev_proof)
    prev_hash = blockchain.hash(prev_block)
    blockchain.add_transaction(sender=node_address, receiver='Hadlein', amount=1)
    #blockchain.add_player(player_name=node_address)
    block = blockchain.create_block(proof, prev_hash)

    response = {'message': 'Congratulations, you just mined a block!',
                'index': block['index'],
                'timestamp': block['timestamp'],
                'proof': block['proof'],
                'prev_hash': block['prev_hash'],
                'transactions': block['transactions'],
                'players': block['players'],
                'alive': block['alive'],
                'vote': block['vote'],
                'killer': block['killer']}
    return jsonify(response), 200

@app.route('/get_chain', methods=['GET'])
def get_chain():
    response = {'chain': blockchain.chain,
                'length': len(blockchain.chain)}
    return jsonify(response), 200

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    json = request.get_json()
    transaction_keys = ['sender', 'receiver', 'amount']
    if not all(key in json for key in transaction_keys):
        return 'Some elements of the transaction are missing!', 400
    index = blockchain.add_transaction(json['sender'], json['receiver'], json['amount'])
    response = {'message': f'This transaction will be added to Block {index}'}
    return jsonify(response), 201

@app.route('/connect_node', methods=['POST'])
def connect_node():
    json = request.get_json()
    nodes = json.get('nodes')
    if nodes is None:
        return "No node", 400
    for node in nodes:
        blockchain.add_node(node)

    response = {'message': 'All the nodes are connected. The Hadcoin blockchain contains the following nodes:',
                'total_nodes': list(blockchain.nodes)}
    return jsonify(response), 201

@app.route('/is_valid', methods=['GET'])
def is_valid():
    is_valid = blockchain.is_chain_valid(blockchain.chain)
    if is_valid:
        response = {'message': "All good, Blockchain is valid!"}
    else:
        response = {'message': 'Houston, we have a problem. The blockchain is not valid!'}
    return jsonify(response), 200

@app.route('/replace_chain', methods=['GET'])
def replace_chain():
    is_chain_replaced = blockchain.replace_chain()
    if is_chain_replaced:
        response = {'message': "The node had a different chain, thus getting replaced by the longest chain",
                    'new_chain': blockchain.chain}
    else:
        response = {'message': 'All good, the chain is the longest one',
                    'actual_chain': blockchain.chain}
    return jsonify(response), 200

@app.route('/enter_game', methods=['GET'])
def enter_game():
    requests.get('http://127.0.0.1:5003/replace_chain')
    prev_block = blockchain.get_prev_block()
    requests.get('http://127.0.0.1:5003/mine_block')
    curr_block = blockchain.get_prev_block()
    
    curr_block['players'] += prev_block['players']
    curr_block['players'].append(node_address)
    
    curr_block['alive'] += prev_block['alive']
    curr_block['alive'].append(1)
    
    curr_block['vote'] += prev_block['vote']
    curr_block['vote'].append(0)
    
    curr_block['killer'] += prev_block['killer']
    curr_block['killer'].append(0)
    
    msg = {'message': 'Hurray, welcome to the game!'}
    return jsonify(msg), 200    


@app.route('/get_role', methods=['GET'])
def get_role():
    requests.get('http://127.0.0.1:5003/replace_chain')
    prev_block = blockchain.get_prev_block()
    requests.get('http://127.0.0.1:5003/mine_block')
    curr_block = blockchain.get_prev_block() 
    curr_block['players'] += prev_block['players']    
    curr_block['alive'] += prev_block['alive']   
    curr_block['vote'] += prev_block['vote']
    curr_block['killer'] += prev_block['killer']
    
    if(sum(curr_block['killer']) != 0):
        for i in range(len(curr_block['players'])):
            if curr_block['players'][i] == node_address:
                index = i
                break
        
        if(curr_block['killer'][index] == 0):
            msg = {'message': 'Hey! you are a villager'}
        else:
            msg = {'message': 'Hey! you are a killer but dont tell anyone'}
    else:
        random_int = random.randint(1, 100)
        random_int = random_int % len(curr_block['players'])
        curr_block['killer'][random_int] = 1
        for i in range(len(curr_block['players'])):
            if curr_block['players'][i] == node_address:
                index = i
                break
        if(curr_block['killer'][index] == 0):
            msg = {'message': 'Hey! you are a villager'}
        else:
            msg = {'message': 'Hey! you are a killer but dont tell anyone'} 
    
    return jsonify(msg), 200


@app.route('/give_vote', methods=['POST'])
def give_vote():
    requests.get('http://127.0.0.1:5003/replace_chain')
    prev_block = blockchain.get_prev_block()
    requests.get('http://127.0.0.1:5003/mine_block')
    curr_block = blockchain.get_prev_block() 
    curr_block['players'] += prev_block['players']    
    curr_block['alive'] += prev_block['alive']   
    curr_block['vote'] += prev_block['vote']
    curr_block['killer'] += prev_block['killer']
    
    for i in range(len(curr_block['players'])):
        if curr_block['players'][i] == node_address:
            index = i
            break
    if curr_block['alive'][index] == 1:
        json = request.get_json()
        index = json.get('voting_against')
        curr_block['vote'][index] += 1
        
        msg = {'message': f'you voted against player no. {index}'}
    else:
        msg = {'message': 'you are not allowed to vote, cause you are no more alive'}
    return jsonify(msg), 201


@app.route('/kill_villager', methods=['POST'])
def kill_villager():
    requests.get('http://127.0.0.1:5003/replace_chain')
    prev_block = blockchain.get_prev_block()
    requests.get('http://127.0.0.1:5003/mine_block')
    curr_block = blockchain.get_prev_block() 
    curr_block['players'] += prev_block['players']    
    curr_block['alive'] += prev_block['alive']   
    curr_block['vote'] += prev_block['vote']
    curr_block['killer'] += prev_block['killer']
    
    for i in range(len(curr_block['players'])):
        if curr_block['players'][i] == node_address:
            index = i
            break
    if curr_block['killer'][index] == 0:
        msg = {'message': 'you are not a killer'}
    else:
        json = request.get_json()
        i = json.get('kill_villager')
        curr_block['alive'][i] = 0
        msg = {'message': f'you killed player no. {i}'}
    return jsonify(msg), 201

@app.route('/get_status', methods=['GET'])
def get_status():
    requests.get('http://127.0.0.1:5003/replace_chain')
    prev_block = blockchain.get_prev_block()
    requests.get('http://127.0.0.1:5003/mine_block')
    curr_block = blockchain.get_prev_block() 
    curr_block['players'] += prev_block['players']    
    curr_block['alive'] += prev_block['alive']   
    curr_block['vote'] += prev_block['vote']
    curr_block['killer'] += prev_block['killer']
    
    threshold = sum(curr_block['alive'])/2
    for i in range(len(curr_block['vote'])):
        if curr_block['vote'][i] > threshold:
            curr_block['alive'][i] = 0
    
    if sum(curr_block['alive']) == 2:
        for i in range(len(curr_block['alive'])):
            if curr_block['alive'][i] == 1:
                if curr_block['killer'][i] == 1:
                    killers_add = curr_block['players'][i]
                    for add in curr_block['players']:
                        if add != killers_add:
                            blockchain.add_transaction(sender = add, receiver = killers_add, amount = 100)
                    msg = {'message': 'killer has won the game, and the prize money has already transactioned to winner!'}
                    return jsonify(msg), 200
        
        msg = {'message': 'villagesr has won the game, and the prize money has already transactioned to winner!'}
        for i in range(len(curr_block['killer'])):
            if curr_block['killer'][i] == 1:
                index = i
                break
        killers_add = curr_block['players'][index]
        for add in curr_block['players']:
            if add != killers_add:
                blockchain.add_transaction(sender = killers_add, receiver = add, amount = 100/(len(curr_block['players'])) - 1)
        
        return jsonify(msg), 200
    
    else:
        for i in range(len(curr_block['alive'])):
            if curr_block['killer'][i] == 1 and curr_block['alive'][i] == 0:
                msg = {'message': 'villagesr has won the game, and the prize money has already transactioned to winner!'} 
                for i in range(len(curr_block['killer'])):
                    if curr_block['killer'][i] == 1:
                        index = i
                        break
                killers_add = curr_block['players'][index]
                for add in curr_block['players']:
                    if add != killers_add:
                        blockchain.add_transaction(sender = killers_add, receiver = add, amount = 100/(len(curr_block['players']) - 1))
                
                return jsonify(msg), 200
            
                
        
        msg = {'message': 'game hasnt finished yet keep playing'}
        prev_block = blockchain.get_prev_block()
        requests.get('http://127.0.0.1:5003/mine_block')
        curr_block = blockchain.get_prev_block() 
        curr_block['players'] += prev_block['players']    
        curr_block['alive'] += prev_block['alive']   
        curr_block['killer'] += prev_block['killer']
        
        for i in range(len(curr_block['players'])):
                    curr_block['vote'].append(0)
        
        
        return jsonify(msg), 200

app.run(host='0.0.0.0', port=5003)
