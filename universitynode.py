# NOde class for Universities, to create and add students to the blockchain.

# -- Imports -- #

import json
import hashlib
import requests
from textwrap import dedent
from time import time
from uuid import uuid4
from flask import Flask, jsonify, request
from urllib.parse import urlparse


# -- Constants -- #

INSTITUTION_INFO_FILE_PATH = './institution.json'


# -- Classes -- #

class UniversityNode(object):
    def __init__(self, institution_properties):
        # Properties all blockchain nodes have
        self.chain = []
        self.current_student_records = []
        self.nodes = set()

        # Private properties (for this node)
        self.institution_name = institution_properties['name']
        self.institution_signature = self.institution_name
        # self.institution_signature = SIGN(self.institution_name)
        self.institution_public_key = institution_properties['public_key']
        self.institution_private_key = institution_properties['private_key']

        # Create the genesis block
        self.append_new_block(self.get_current_block(proof=100, previous_hash=1))


    def get_current_block(self, proof, previous_hash=None):
        # Creates a new Block and adds it to the chain
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'student_records': self.current_student_records,
            'proof': proof,
            'previous_hash': previous_hash or UniversityNode.hash(self.chain[-1]),
        }
        return block

    
    def add_new_record(self, first_name, last_name, id_number, date_enrolled_through):
        # Adds a new record to the list of transactions
        new_record_contents = {
            'institution_name': self.institution_name,
            'institution_signature': self.institution_signature,
            'first_name': first_name,
            'last_name': last_name,
            'id_number': id_number,
            'date_enrolled_through': date_enrolled_through,            
        }
        self.current_student_records.append({
            'contents': new_record_contents,
            'contents_signature': self.institution_name
            # 'contents_signature': SIGN(self.institution_name)
        })
        return self.last_block['index'] + 1 # ???


    def append_new_block(self, block, reset=False):
        self.chain.append(block)
        if reset:
            self.current_student_records = []


    def proof_of_work(self):
        # Find a proof that works for this block 
        # This is a hard task
        # Returns a valid block
        proof = 0
        current_block = self.get_current_block(proof)
        while UniversityNode.valid_block_proof(current_block) is False:
            proof += 1
            current_block = self.get_current_block(proof)
        return current_block


    # def broadcast(self, block, block_hash):
    #     for node in self.nodes:
    #         block_package = {
    #             'block': block,
    #             'hash': block_hash
    #         }
    #         response = requests.post(f'http://{node}/chain', data=block_package)


    def register_node(self, address):
        """
        Add a new node to the list of nodes
        :param address: <str> Address of node. Eg. 'http://192.168.0.5:5000'
        :return: None
        """
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)


    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid
        :param chain: <list> A blockchain
        :return: <bool> True if valid, False if not
        """
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print('{last_block}')
            print('{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            if block['previous_hash'] != UniversityNode.hash(last_block):
                return False

            # Check that the Proof of Work is correct
            if not UniversityNode.valid_block_proof(block):
                return False

            last_block = block
            current_index += 1
        return True


    def resolve_conflicts(self): # how does this work with broadcasting
        """
        This is our Consensus Algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        :return: <bool> True if our chain was replaced, False if not
        """
        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get('http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True

        return False


    @property
    def last_block(self):
        # Returns the last Block in the chain
        return self.chain[-1]


    @staticmethod
    def valid_block_proof(block):
        # Check if the inputted block has valid proof
        block_hash = UniversityNode.hash(block)
        return block_hash[:4] == "0000"


    # @staticmethod
    # def valid_proof(last_proof, proof): # not quite, correct, needs to be on the block
    #     """
    #     Validates the Proof: Does hash(last_proof, proof) contain 4 leading zeroes?
    #     :param last_proof: <int> Previous Proof
    #     :param proof: <int> Current Proof
    #     :return: <bool> True if correct, False if not.
    #     """
    #     guess = f'{last_proof}{proof}'.encode()
    #     guess_hash = hashlib.sha256(guess).hexdigest()
    #     return guess_hash[:4] == "0000"


    @staticmethod
    def hash(block):
        # Hashes a Block
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()


# -- Endpoints -- #


# Instantiate our Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Node
with open(INSTITUTION_INFO_FILE_PATH) as data_file:    
    institution_properties = json.load(data_file)
node = UniversityNode(institution_properties)


@app.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to get a valid block
    valid_block = node.proof_of_work()
    block_hash = UniversityNode.hash(valid_block)
    node.append_new_block(valid_block, reset=True)

    # node.broadcast(valid_block, block_hash)

    response = {
        'message': "New Block Forged",
        'block': valid_block,
        'hash': block_hash,
    }
    return jsonify(response), 200

  
@app.route('/record/new', methods=['POST'])
def new_record():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['first_name', 'last_name', 'id_number', 'date_enrolled_through']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index = node.add_new_record(values['first_name'], values['last_name'], values['id_number'], values['date_enrolled_through'])

    response = {'message': 'Transaction will be added to Block {index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': node.chain,
        'length': len(node.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        node.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(node.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = node.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': node.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': node.chain
        }
    return jsonify(response), 200


# @app.route('/nodes/accept_block', methods=['POST'])
# def accept():
#     values = request.get_json()

#     required = ['block', 'hash']
#     if not all(k in values for k in required):
#         return 'Missing values', 400

#     if not UniversityNode.valid_block_proof(values['block']):
#         return 'Not a valid block proof', 400

#     if values['hash'] != UniversityNode.hash(values['block']):
#         return 'Broadcasted hash does not match block\'s hash', 400

#     node.append_new_block(values['block'])
#     response = {
#         'message': 'New block appended',
#         'block': values['block']
#     }
#     return jsonify(response), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

