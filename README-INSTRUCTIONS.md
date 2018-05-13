# UniversityBlockchain
Identity verification for students of universities built on top of the blockchain.

How to use StudentChain prototype:

- Install python 3, the Flask web framework, and the requests library
- Run "python3 uninode2.py" - you are now a university node on the blockchain! Spectator nodes can be set up similarly but will not have any add functionality.
- Go to "http://localhost:5000/add/" to access the form for adding a student as a university node
- After adding one or more student, click "Mine" to mine a new block in the blockchain storing records of all the students recently added.
- Go to "http://localhost:5000/check" to verify someone's student status. Enter their information and click "Check Student" to check if they are a student on this blockchain.
- Go to "http://localhost:5000/chain" to view the entire blockchain at any given time.
- To connect an additional node, repeat steps 1 and 2 and be sure to click "resolve" in the check page before attempting to verify students from the new node.

