# Soroban Smart Contract Integration Test Flow

## Overview
This document provides comprehensive instructions for integration testing of Soroban smart contract flows within the Stellar Hummingbot connector. These tests validate end-to-end functionality across contract deployment, invocation, and state management.

**QA_IDs**: REQ-SOB-001 through REQ-SOB-007  
**Test Environment**: Testnet or Local Stellar Network  
**Prerequisites**: Deployed test contracts, funded test accounts

## Test Environment Setup

### Local Stellar Network (Quickstart)
```bash
# Start local Stellar network with Soroban support
docker run --rm -it -p 8000:8000 \
  --name stellar \
  stellar/quickstart:soroban-dev@sha256:... \
  --standalone \
  --enable-soroban-rpc

# Verify RPC endpoint
curl http://localhost:8000/soroban/rpc \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"getHealth"}'
```

### Testnet Configuration
```python
# tests/integration/conftest.py
SOROBAN_RPC_URL = "https://soroban-testnet.stellar.org"
NETWORK_PASSPHRASE = "Test SDF Network ; September 2015"
HORIZON_URL = "https://horizon-testnet.stellar.org"
```

## Contract Deployment Flow

### Test Contract: AMM Pool Manager
```javascript
// contracts/amm_pool.js (WASM contract)
use soroban_sdk::{contract, contractimpl, Env, Symbol, Vec};

#[contract]
pub struct AMMPool;

#[contractimpl]
impl AMMPool {
    pub fn initialize(env: Env, token_a: Symbol, token_b: Symbol) -> bool {
        // Pool initialization logic
        true
    }
    
    pub fn add_liquidity(env: Env, amount_a: i64, amount_b: i64) -> i64 {
        // Add liquidity and return LP tokens
        amount_a + amount_b
    }
    
    pub fn swap(env: Env, token_in: Symbol, amount_in: i64) -> i64 {
        // Swap logic with 0.3% fee
        (amount_in * 997) / 1000
    }
}
```

### Deployment Test
```python
# tests/integration/test_soroban_deployment.py
import pytest
from stellar_sdk import Keypair, Network, TransactionBuilder
from stellar_sdk.soroban import SorobanServer

class TestSorobanDeployment:
    """Integration tests for Soroban contract deployment."""
    
    async def test_amm_contract_deployment(self, soroban_server, test_account):
        """Deploy AMM contract and verify initialization.
        
        QA_ID: REQ-SOB-001
        Acceptance Criteria: 
        - assert contract.address is not None
        - assert contract.status == "ACTIVE"
        """
        # Load WASM bytecode
        with open("contracts/amm_pool.wasm", "rb") as f:
            wasm_code = f.read()
        
        # Deploy contract
        deploy_tx = (
            TransactionBuilder(
                source_account=test_account,
                network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE,
                base_fee=1000000
            )
            .append_install_contract_code_op(contract=wasm_code)
            .set_timeout(30)
            .build()
        )
        
        deploy_tx.sign(test_account.keypair)
        response = await soroban_server.send_transaction(deploy_tx)
        
        # Verify deployment
        assert response.status == "SUCCESS"
        assert response.result_xdr is not None
        
        contract_id = response.contract_id
        assert contract_id is not None
        assert len(contract_id) == 56  # Stellar contract ID format
```

## End-to-End Trading Flow Tests

### AMM Liquidity Pool Integration
```python
# tests/integration/test_soroban_amm_flow.py
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock

class TestSorobanAMMFlow:
    """End-to-end AMM trading flow tests."""
    
    async def test_add_liquidity_full_flow(self, connector, amm_contract):
        """Test complete add liquidity flow with Soroban contract.
        
        QA_ID: REQ-SOB-003
        Acceptance Criteria:
        - assert lp_tokens > Decimal('0')
        - assert pool.reserves_a == expected_reserve_a
        - assert pool.reserves_b == expected_reserve_b
        """
        # Setup test tokens
        token_a = "USDC:GCKFBEIYTKP73V73JDICGCBVZHL6QGLXWDMNNUFRT2GZPKFR4YZTDC4MJ"
        token_b = "XLM:native"
        
        # Initialize pool
        init_response = await connector.soroban_client.invoke_contract(
            contract_id=amm_contract.address,
            method="initialize",
            args=[token_a, token_b]
        )
        assert init_response.success == True
        
        # Add liquidity
        liquidity_amount_a = Decimal('1000')
        liquidity_amount_b = Decimal('5000')  # 1 USDC = 5 XLM
        
        add_liquidity_response = await connector.soroban_client.invoke_contract(
            contract_id=amm_contract.address,
            method="add_liquidity",
            args=[liquidity_amount_a, liquidity_amount_b]
        )
        
        # Verify liquidity addition
        assert add_liquidity_response.success == True
        lp_tokens = Decimal(add_liquidity_response.result['lp_tokens'])
        assert lp_tokens > Decimal('0')
        assert lp_tokens == (liquidity_amount_a * liquidity_amount_b).sqrt()
        
        # Verify pool state
        pool_state = await connector.soroban_client.invoke_contract(
            contract_id=amm_contract.address,
            method="get_reserves"
        )
        assert Decimal(pool_state.result['reserve_a']) == liquidity_amount_a
        assert Decimal(pool_state.result['reserve_b']) == liquidity_amount_b
    
    async def test_swap_execution_with_slippage_protection(self, connector, amm_contract):
        """Test swap execution with slippage protection.
        
        QA_ID: REQ-SOB-004
        Acceptance Criteria:
        - assert swap_result.amount_out >= min_amount_out
        - assert swap_result.price_impact <= max_slippage
        - assert swap_result.gas_used < MAX_GAS_LIMIT
        """
        # Pre-setup: Pool with liquidity
        await self._setup_pool_with_liquidity(connector, amm_contract)
        
        # Swap parameters
        token_in = "USDC:GCKFBEIYTKP73V73JDICGCBVZHL6QGLXWDMNNUFRT2GZPKFR4YZTDC4MJ"
        amount_in = Decimal('100')
        max_slippage = Decimal('0.005')  # 0.5%
        
        # Calculate expected output (with 0.3% fee)
        expected_out = await connector._calculate_swap_output(
            amm_contract.address, token_in, amount_in
        )
        min_amount_out = expected_out * (Decimal('1') - max_slippage)
        
        # Execute swap
        swap_response = await connector.soroban_client.invoke_contract(
            contract_id=amm_contract.address,
            method="swap",
            args=[token_in, amount_in, min_amount_out]
        )
        
        # Verify swap execution
        assert swap_response.success == True
        swap_result = swap_response.result
        
        assert Decimal(swap_result['amount_out']) >= min_amount_out
        assert Decimal(swap_result['price_impact']) <= max_slippage
        assert int(swap_result['gas_used']) < 1000000  # 1M gas limit
        
        # Verify fee collection
        assert Decimal(swap_result['fee_collected']) == amount_in * Decimal('0.003')
```

## Path Payment Integration Tests

### Multi-Hop Path Finding
```python
# tests/integration/test_soroban_path_payments.py
class TestSorobanPathPayments:
    """Integration tests for Soroban-powered path payments."""
    
    async def test_multi_hop_path_execution(self, connector, path_engine):
        """Test multi-hop path payment through Soroban contracts.
        
        QA_ID: REQ-SOB-005
        Acceptance Criteria:
        - assert path.hops >= 2
        - assert final_amount >= min_destination_amount
        - assert execution_time < 10.0  # seconds
        """
        # Setup multi-hop path: USDC -> XLM -> BTC
        source_asset = "USDC:GCKFBEIYTKP73V73JDICGCBVZHL6QGLXWDMNNUFRT2GZPKFR4YZTDC4MJ"
        dest_asset = "BTC:GATEMHCCKCY67ZUCKTROYN24ZYT5GK4EQZ65JJLDHKHRUZI3EUEKMTCH"
        send_amount = Decimal('1000')
        min_dest_amount = Decimal('0.015')  # Minimum BTC expected
        
        # Find optimal path
        path = await path_engine.find_payment_path(
            source_asset=source_asset,
            dest_asset=dest_asset,
            send_amount=send_amount
        )
        
        # Verify path structure
        assert len(path.hops) >= 2
        assert path.hops[0].asset == source_asset
        assert path.hops[-1].asset == dest_asset
        
        # Execute path payment
        start_time = time.time()
        
        payment_result = await connector.execute_path_payment(
            source_asset=source_asset,
            dest_asset=dest_asset,
            send_amount=send_amount,
            dest_min=min_dest_amount,
            path=path.contracts
        )
        
        execution_time = time.time() - start_time
        
        # Verify execution
        assert payment_result.success == True
        assert Decimal(payment_result.dest_amount) >= min_dest_amount
        assert execution_time < 10.0  # Performance requirement
        
        # Verify intermediate contract calls
        for hop in path.hops[:-1]:
            contract_state = await connector.soroban_client.get_contract_data(
                contract_id=hop.contract_id,
                key="last_swap_timestamp"
            )
            assert int(contract_state.value) > start_time
```

## Cross-Contract Composition Tests

### Flash Loan + Arbitrage Flow
```python
# tests/integration/test_soroban_flash_arbitrage.py
class TestSorobanFlashArbitrage:
    """Integration tests for flash loan arbitrage via Soroban."""
    
    async def test_flash_loan_arbitrage_execution(self, connector, flash_contract, amm_contracts):
        """Test flash loan arbitrage across multiple AMM contracts.
        
        QA_ID: REQ-SOB-006
        Acceptance Criteria:
        - assert arbitrage_profit > Decimal('0')
        - assert flash_loan.repaid == True
        - assert arbitrage_profit > gas_costs + fees
        """
        # Detect arbitrage opportunity
        opportunity = await connector.arbitrage_detector.find_opportunities()
        assert len(opportunity) > 0
        
        best_arb = opportunity[0]
        assert best_arb.profit_percentage > Decimal('0.001')  # 0.1% minimum
        
        # Execute flash loan arbitrage
        flash_amount = best_arb.max_trade_size
        
        arbitrage_result = await connector.soroban_client.invoke_contract(
            contract_id=flash_contract.address,
            method="execute_arbitrage",
            args=[
                flash_amount,
                best_arb.source_pool,
                best_arb.dest_pool,
                best_arb.asset_path
            ]
        )
        
        # Verify successful arbitrage
        assert arbitrage_result.success == True
        
        profit = Decimal(arbitrage_result.result['net_profit'])
        gas_costs = Decimal(arbitrage_result.gas_used) * Decimal('0.00001')  # Gas price
        total_fees = Decimal(arbitrage_result.result['total_fees'])
        
        assert profit > Decimal('0')
        assert profit > gas_costs + total_fees
        
        # Verify flash loan repayment
        flash_loan_status = arbitrage_result.result['flash_loan_status']
        assert flash_loan_status['repaid'] == True
        assert flash_loan_status['interest_paid'] > Decimal('0')
```

## Performance and Load Testing

### Contract Invocation Performance
```python
# tests/integration/test_soroban_performance.py
class TestSorobanPerformance:
    """Performance tests for Soroban contract operations."""
    
    async def test_contract_invocation_latency(self, connector, amm_contract):
        """Test contract invocation latency under load.
        
        QA_ID: REQ-SOB-007
        Acceptance Criteria:
        - assert avg_latency < 2.0  # seconds
        - assert p95_latency < 5.0  # seconds
        - assert success_rate > 0.99  # 99%
        """
        latencies = []
        successes = 0
        total_calls = 100
        
        for i in range(total_calls):
            start_time = time.time()
            
            try:
                result = await connector.soroban_client.invoke_contract(
                    contract_id=amm_contract.address,
                    method="get_reserves"
                )
                
                if result.success:
                    successes += 1
                    
            except Exception as e:
                logger.warning(f"Contract call {i} failed: {e}")
            
            latency = time.time() - start_time
            latencies.append(latency)
            
            # Rate limiting
            await asyncio.sleep(0.1)
        
        # Calculate metrics
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        success_rate = successes / total_calls
        
        # Verify performance SLAs
        assert avg_latency < 2.0, f"Average latency {avg_latency}s exceeds 2s limit"
        assert p95_latency < 5.0, f"P95 latency {p95_latency}s exceeds 5s limit"
        assert success_rate > 0.99, f"Success rate {success_rate} below 99%"
```

## Test Execution Instructions

### Local Development
```bash
# Install Soroban CLI
cargo install --locked soroban-cli

# Build test contracts
cd contracts/
soroban contract build

# Deploy to local network
soroban contract deploy --wasm target/wasm32-unknown-unknown/release/amm_pool.wasm --source alice --network standalone

# Run integration tests
pytest tests/integration/ -v -s --network=local
```

### Testnet Execution
```bash
# Configure testnet
export SOROBAN_NETWORK_PASSPHRASE="Test SDF Network ; September 2015"
export SOROBAN_RPC_URL="https://soroban-testnet.stellar.org"

# Fund test accounts
soroban keys fund alice --network testnet

# Deploy contracts to testnet
soroban contract deploy --wasm amm_pool.wasm --source alice --network testnet

# Run testnet integration tests
pytest tests/integration/ -v --network=testnet --slow
```

### CI Pipeline Integration
```yaml
# In .github/workflows/ci.yml
integration-tests:
  runs-on: ubuntu-latest
  services:
    stellar:
      image: stellar/quickstart:soroban-dev
      ports:
        - 8000:8000
      options: --standalone --enable-soroban-rpc
  
  steps:
    - name: Run Soroban Integration Tests
      run: |
        pytest tests/integration/ -v --network=ci \
          --soroban-rpc=http://localhost:8000/soroban/rpc
```

## Test Data Management

### Contract State Fixtures
```python
# tests/integration/fixtures/contract_states.py
INITIAL_AMM_STATE = {
    "token_a": "USDC:GCKFBEIYTKP73V73JDICGCBVZHL6QGLXWDMNNUFRT2GZPKFR4YZTDC4MJ",
    "token_b": "XLM:native",
    "reserve_a": "10000000000",  # 1,000 USDC (7 decimals)
    "reserve_b": "50000000000",  # 5,000 XLM (7 decimals)
    "total_supply": "22360679775",  # sqrt(1000 * 5000) * 10^7
    "fee_rate": "3000"  # 0.3%
}

ARBITRAGE_OPPORTUNITY_FIXTURE = {
    "source_pool": "CCJZ5DGASBWQXR5MPFCJIXJCMF3GZGCQ5VCQPBQJ5RPCJBZMKZF6LJP3",
    "dest_pool": "CBJZ5DGASBWQXR5MPFCJIXJCMF3GZGCQ5VCQPBQJ5RPCJBZMKZF6LJP4",
    "asset": "USDC:GCKFBEIYTKP73V73JDICGCBVZHL6QGLXWDMNNUFRT2GZPKFR4YZTDC4MJ",
    "price_difference": "0.0025",  # 0.25%
    "max_trade_size": "50000000000"  # 500 USDC
}
```

## Troubleshooting Guide

### Common Issues
1. **Contract not found**: Verify contract deployment and ID
2. **Gas limit exceeded**: Increase gas limit or optimize contract calls
3. **Network timeout**: Check RPC endpoint health and network connectivity
4. **State inconsistency**: Ensure proper test isolation and cleanup

### Debug Commands
```bash
# Check contract state
soroban contract invoke --id $CONTRACT_ID --source alice --network testnet -- get_reserves

# Monitor transaction
soroban events --start-ledger $LEDGER --contract $CONTRACT_ID --network testnet

# Verify account balance
soroban keys address alice | xargs curl -s "https://horizon-testnet.stellar.org/accounts/{}"
```