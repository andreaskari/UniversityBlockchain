import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import requests
from flask import Flask, jsonify, request, render_template
from Crypto.PublicKey import RSA
import crypto
from threading import Thread

INSTITUTION_INFO_FILE_PATH = './institution.json'
PUBLIC_KEYS_FILE_PATH = './publickeys.json'


class UniversityNode:
    def __init__(self, institution_properties, keyfile):
        self.current_students = []
        self.chain = []
        self.nodes = set()

        # Private properties (for this node)
        self.institution_name = institution_properties['name']
        self.institution_signature = self.institution_name
        # self.institution_signature = SIGN(self.institution_name)
        self.institution_public_key = institution_properties['public_key']
        self.institution_private_key = institution_properties['private_key']
        self.ciph = crypto.Crypto()
        self.pubKey = RSA.importKey(self.institution_public_key)
        self.privKey = RSA.importKey(self.institution_private_key)

        # Create the genesis block
        self.new_block(previous_hash='1', proof=100)

    def register_node(self, address):
        """
        Add a new node to the list of nodes
        :param address: Address of node. Eg. 'http://192.168.0.5:5000'
        """

        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')


    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid
        :param chain: A blockchain
        :return: True if valid, False if not
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof'], block['previous_hash']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        This is our consensus algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        :return: True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)
        print(neighbours)
        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

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

    def new_block(self, proof, previous_hash):
        """
        Create a new Block in the Blockchain
        :param proof: The proof given by the Proof of Work algorithm
        :param previous_hash: Hash of previous Block
        :return: New Block
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'students': self.current_students,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Reset the current list of transactions
        self.current_students = []

        self.chain.append(block)

        return block

    def new_transaction(self, sender, recipient, amount, date):
        """
        Creates a new transaction to go into the next mined Block
        :param sender: Address of the Sender
        :param recipient: Address of the Recipient
        :param amount: Amount
        :return: The index of the Block that will hold this transaction
        """
        transaction = {
            'first_name': sender,
            'last_name': recipient,
            'student_id': amount,
            'date_enrolled_through': date,
            'institution_name': self.institution_name
        }
        sign_string = str(sender) + str(recipient) + str(amount) + str(date) + str(self.institution_name)
        transaction['signature'] = self.ciph.asymmetric_sign(str(sign_string), self.privKey)
        self.current_students.append(transaction)
        # new_one = dict(transaction)
        # sig = new_one['signature']
        # new_one.pop('signature', None)
        # print(new_one)
        # print(transaction)
        # verified = self.ciph.asymmetric_verify(str(new_one), sig, self.pubKey)
        # print(verified)
        # MAKE SURE TO SIGN THE NEW TRANSACTION.
        # self.current_student_records.append({
        #     'contents': new_record_contents,
        #     'contents_signature': self.institution_name
        #     # 'contents_signature': SIGN(self.institution_name)
        # })
        return self.last_block['index'] + 1

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block
        :param block: Block
        """

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_block):
        """
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes
         - Where p is the previous proof, and p' is the new proof
         
        :param last_block: <dict> last Block
        :return: <int>
        """

        last_proof = last_block['proof']
        last_hash = self.hash(last_block)

        proof = 0
        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof, last_hash):
        """
        Validates the Proof
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :param last_hash: <str> The hash of the Previous Block
        :return: <bool> True if correct, False if not.
        """

        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"


# Instantiate the Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

node = None

@app.route('/mine', methods=['GET'])
def mine():
    global node
    # We run the proof of work algorithm to get the next proof...
    last_block = node.last_block
    proof = node.proof_of_work(last_block)

    # Forge the new Block by adding it to the chain
    previous_hash = node.hash(last_block)
    block = node.new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'students': block['students'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200


@app.route('/student/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['first_name', 'last_name', 'student_id', 'date_enrolled_through']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index = node.new_transaction(values['first_name'], values['last_name'], values['student_id'], values['date_enrolled_through'])

    response = {'message': f'Transaction will be added to Block {index}'}
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

    endpoints = values.get('nodes')
    if endpoints is None:
        return "Error: Please supply a valid list of nodes", 400

    for endpoint in endpoints:
        node.register_node(endpoint)

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

@app.route('/verify', methods=['POST'])
def verify_student():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['first_name', 'last_name', 'student_id']
    if not all(k in values for k in required):
        return 'Missing values', 400

    for block in node.chain:
        student_list = block['students']
        for student in student_list:
            if student['first_name'] == values['first_name'] and student['last_name'] == values['last_name'] and student['student_id'] == values['student_id']:
                # check sig
                new_one = dict(student)
                sig = new_one['signature']
                new_one.pop('signature', None)
                with open(PUBLIC_KEYS_FILE_PATH) as pub_file:    
                    pub_properties = json.load(pub_file, strict=False)
                school_pub_key = RSA.importKey(pub_properties[student['institution_name']])
                sign_string = str(student['first_name']) + str(student['last_name']) + str(student['student_id']) + str(student['date_enrolled_through']) + str(student['institution_name'])
                verified = node.ciph.asymmetric_verify(str(sign_string), sig, school_pub_key)
                if verified:
                    print({"result" : True, "school" : student['institution_name'], "signature": sig})
                    return jsonify({"result" : True, "school" : student['institution_name'], "signature": sig}), 200
    print({"result" : False})
    return jsonify({"result" : False}), 200

@app.route('/add/')
def add():
    return render_template('add.html')

@app.route('/check')
def check():
    return render_template('check.html')

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    parser.add_argument('-i', '--institution', default="berkeley", type=str, help='your institution')
    args = parser.parse_args()
    port = args.port
    INSTITUTION_INFO_FILE_PATH = './' + args.institution + '.json'
    with open(INSTITUTION_INFO_FILE_PATH) as data_file:    
        institution_properties = json.load(data_file, strict=False)
    node = UniversityNode(institution_properties, args.institution)
    app.run(host='0.0.0.0', port=port)