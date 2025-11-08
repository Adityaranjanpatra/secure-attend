"""
Blockchain Implementation Module
Provides tamper-proof attendance record storage
"""

import hashlib
import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional


class Block:
    """Individual block in the blockchain"""

    def __init__(self, index: int, timestamp: str, data: Dict, previous_hash: str):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """Calculate SHA-256 hash of block contents"""
        block_string = f"{self.index}{self.timestamp}{json.dumps(self.data, sort_keys=True)}{self.previous_hash}{self.nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty: int = 2):
        """Mine block with Proof-of-Work"""
        target = "0" * difficulty

        print(f"⛏ Mining block {self.index}...", end=" ")

        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()

        print(f"✓ Mined! Hash: {self.hash[:16]}... (nonce: {self.nonce})")

    def to_dict(self) -> Dict:
        """Convert block to dictionary"""
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'data': self.data,
            'previous_hash': self.previous_hash,
            'hash': self.hash,
            'nonce': self.nonce
        }

    def __repr__(self):
        return f"Block(index={self.index}, hash={self.hash[:8]}...)"


class Blockchain:
    """Blockchain for immutable attendance records"""

    def __init__(self, blockchain_file: str = "blockchain_data.json"):
        self.blockchain_file = Path(blockchain_file)
        self.chain: List[Block] = []
        self.difficulty = 2

        self.load_chain()

        if not self.chain:
            self.create_genesis_block()

    def create_genesis_block(self):
        """Create the first block in the chain"""
        print("Creating genesis block...")

        genesis_data = {
            "type": "genesis",
            "message": "SecureAttend Blockchain Initialized",
            "version": "3.0",
            "created": datetime.datetime.now().isoformat()
        }

        genesis_block = Block(0, str(datetime.datetime.now()), genesis_data, "0")
        genesis_block.mine_block(self.difficulty)

        self.chain.append(genesis_block)
        self.save_chain()

        print("✓ Genesis block created")

    def get_latest_block(self) -> Optional[Block]:
        """Get the most recent block"""
        return self.chain[-1] if self.chain else None

    def add_block(self, data: Dict) -> Optional[str]:
        """Add new attendance record to blockchain"""
        try:
            latest_block = self.get_latest_block()

            if not latest_block:
                print("✗ No genesis block found")
                return None

            new_block = Block(
                index=len(self.chain),
                timestamp=str(datetime.datetime.now()),
                data=data,
                previous_hash=latest_block.hash
            )

            new_block.mine_block(self.difficulty)
            self.chain.append(new_block)
            self.save_chain()

            return new_block.hash

        except Exception as e:
            print(f"✗ Block addition error: {e}")
            return None

    def is_chain_valid(self) -> bool:
        """Verify blockchain integrity"""
        print("Verifying blockchain integrity...")

        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            # Check if current block hash is correct
            if current_block.hash != current_block.calculate_hash():
                print(f"✗ Block {i} has invalid hash")
                return False

            # Check if previous hash reference is correct
            if current_block.previous_hash != previous_block.hash:
                print(f"✗ Block {i} has invalid previous hash reference")
                return False

        print("✓ Blockchain is valid")
        return True

    def save_chain(self):
        """Save blockchain to file"""
        try:
            chain_data = [block.to_dict() for block in self.chain]

            with open(self.blockchain_file, 'w') as f:
                json.dump(chain_data, f, indent=4)

        except Exception as e:
            print(f"✗ Chain save error: {e}")

    def load_chain(self):
        """Load blockchain from file"""
        try:
            if self.blockchain_file.exists():
                with open(self.blockchain_file, 'r') as f:
                    chain_data = json.load(f)

                self.chain = []
                for block_dict in chain_data:
                    block = Block(
                        block_dict['index'],
                        block_dict['timestamp'],
                        block_dict['data'],
                        block_dict['previous_hash']
                    )
                    block.hash = block_dict['hash']
                    block.nonce = block_dict['nonce']
                    self.chain.append(block)

                print(f"✓ Loaded {len(self.chain)} blocks from blockchain")

        except Exception as e:
            print(f"✗ Chain load error: {e}")
            self.chain = []

    def get_block_by_hash(self, block_hash: str) -> Optional[Block]:
        """Find block by hash"""
        for block in self.chain:
            if block.hash == block_hash:
                return block
        return None

    def get_attendance_records(self) -> List[Dict]:
        """Extract all attendance records from blockchain"""
        records = []

        for block in self.chain[1:]:  # Skip genesis block
            if block.data.get('type') == 'attendance':
                records.append(block.data)

        return records

    def __len__(self):
        return len(self.chain)

    def __repr__(self):
        return f"Blockchain(blocks={len(self.chain)}, valid={self.is_chain_valid()})"


# Test the blockchain
if __name__ == "__main__":
    print("Testing Blockchain Implementation\n")

    # Create blockchain
    bc = Blockchain("test_blockchain.json")

    # Add test attendance records
    test_records = [
        {
            "type": "attendance",
            "user_id": "john_doe",
            "name": "John Doe",
            "timestamp": datetime.datetime.now().isoformat(),
            "liveness_score": 0.95,
            "emotion": "Happy"
        },
        {
            "type": "attendance",
            "user_id": "jane_smith",
            "name": "Jane Smith",
            "timestamp": datetime.datetime.now().isoformat(),
            "liveness_score": 0.88,
            "emotion": "Neutral"
        }
    ]

    for record in test_records:
        block_hash = bc.add_block(record)
        print(f"Added record for {record['name']}, hash: {block_hash[:16]}...")

    # Verify chain
    print(f"\n{bc}")
    bc.is_chain_valid()

    # Get all attendance records
    print(f"\nTotal attendance records: {len(bc.get_attendance_records())}")