# NOde class for Universities, to create and add students to the blockchain.

# -- Imports -- #

import json
import hashlib
from textwrap import dedent
from time import time
from uuid import uuid4
from flask import Flask


# -- Classes -- #

class UniversityNode(object):
    def __init__(self, institution_name):
        # Properties all blockchain nodes have
        self.chain = []
        self.current_student_records = []

        # Create the genesis block
        self.new_block(previous_hash=1, proof=100)

        # Private properties (for this node)
        self.institution_name = institution_name
        self.institution_signature = SIGN(self.institution_name)
        

    def get_current_block(self, proof):
        # Creates a new Block and adds it to the chain
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'student_records': self.current_student_records,
            'proof': proof,
            'previous_hash': self.hash(self.chain[-1]),
        }
        return block

    
    def new_record(self, first_name, last_name, id_number, date_enrolled_through):
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
            'contents_signature': SIGN(self.institution_name)
        })
        return self.last_block['index'] + 1 # ???
    

    def broadcast_our_block(block):
        BROADCAST(block)
        self.current_student_records = []
        self.append_new_block(block)


    def append_new_block(block):
        self.chain.append(block)


    def proof_of_work(self, last_proof):
        # Find a proof that works for this block 
        # This is a hard task
        proof = 0
        current_block = self.get_current_block(proof)
        while valid_block_proof(current_block) is False:
            proof += 1
            current_block = self.get_current_block(proof)
        return proof


    @staticmethod
    def valid_block_proof(block):
        # Check if the inputted block has valid proof
        block_hash = hash(block)
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


    @property
    def last_block(self):
        # Returns the last Block in the chain
        return self.chain[-1]


# -- Endpoints -- #


# Instantiate our Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
node = UniversityNode()


@app.route('/mine', methods=['GET'])
def mine():
    return "We'll mine a new Block"
  
@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    return "We'll add a new transaction"

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

