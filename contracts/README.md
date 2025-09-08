# Smart Contracts

This directory contains Soroban smart contracts for the Stellar Hummingbot Connector.

## Contracts

- `amm_pool.wasm` - AMM pool contract for testing (to be added)
- `arbitrage.wasm` - Cross-contract arbitrage contract (to be added)

## Development

Contracts are built using the Soroban CLI and deployed for testing purposes.

```bash
soroban contract build
soroban contract deploy --wasm contract.wasm --network testnet
```

## Testing

Integration tests automatically deploy test contracts when available.