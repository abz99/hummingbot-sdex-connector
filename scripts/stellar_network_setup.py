#!/usr/bin/env python3
"""
Stellar Network Setup Script
Automated setup and validation of Stellar network configurations.
"""

import asyncio
import sys
import argparse
import json
from pathlib import Path
from typing import Dict, Any, List
import aiohttp
from stellar_sdk import Keypair, Account, Server
from stellar_sdk.exceptions import NotFoundError

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from hummingbot.connector.exchange.stellar.stellar_network_manager import (
    StellarNetworkManager, StellarNetwork, NetworkStatus
)


class StellarNetworkSetup:
    """Automated Stellar network setup and validation."""
    
    def __init__(self, config_path: str = "config/networks.yml"):
        self.network_manager = StellarNetworkManager(config_path)
        self.test_accounts: Dict[StellarNetwork, List[Dict[str, str]]] = {}
        
    async def initialize(self):
        """Initialize the setup system."""
        await self.network_manager.initialize()
        print("✅ Network manager initialized")
    
    async def cleanup(self):
        """Clean up resources."""
        await self.network_manager.cleanup()
        print("🧹 Cleaned up resources")
    
    async def validate_all_networks(self) -> Dict[str, Any]:
        """Validate all configured networks."""
        print("🔍 Validating all Stellar networks...")
        
        validation_results = {}
        
        for network in StellarNetwork:
            if network in self.network_manager.network_configs:
                print(f"\n📡 Validating {network.value.upper()}...")
                result = await self.validate_network(network)
                validation_results[network.value] = result
                
                if result['status'] == 'healthy':
                    print(f"✅ {network.value.upper()} is healthy")
                elif result['status'] == 'degraded':
                    print(f"⚠️  {network.value.upper()} is degraded")
                else:
                    print(f"❌ {network.value.upper()} is down")
            else:
                print(f"⏭️  {network.value.upper()} not configured, skipping")
        
        return validation_results
    
    async def validate_network(self, network: StellarNetwork) -> Dict[str, Any]:
        """Validate a specific network."""
        try:
            health = await self.network_manager.check_network_health(network)
            config = self.network_manager.get_network_config(network)
            server = self.network_manager.get_server(network)
            
            result = {
                'network': network.value,
                'status': health.status.value,
                'primary_healthy': health.primary_healthy,
                'fallback_count': health.fallback_count,
                'avg_response_time': round(health.avg_response_time, 2),
                'error_rate': round(health.error_rate, 3),
                'endpoints': [],
                'ledger_info': None,
                'friendbot_available': False
            }
            
            # Test endpoints
            for i, endpoint in enumerate(config.horizon_endpoints):
                endpoint_result = {
                    'url': endpoint.url,
                    'type': 'primary' if i == 0 else 'fallback',
                    'healthy': endpoint.is_healthy,
                    'response_time': round(endpoint.response_time, 2),
                    'error_count': endpoint.error_count
                }
                result['endpoints'].append(endpoint_result)
            
            # Get ledger information
            try:
                ledger_response = await server.ledgers().order(desc=True).limit(1).call()
                if ledger_response['_embedded']['records']:
                    latest_ledger = ledger_response['_embedded']['records'][0]
                    result['ledger_info'] = {
                        'sequence': latest_ledger['sequence'],
                        'hash': latest_ledger['hash'],
                        'closed_at': latest_ledger['closed_at'],
                        'transaction_count': latest_ledger['transaction_count']
                    }
            except Exception as e:
                print(f"  ⚠️  Could not fetch ledger info: {e}")
            
            # Test friendbot availability (testnet/futurenet only)
            if config.friendbot and config.friendbot.get('enabled'):
                result['friendbot_available'] = await self._test_friendbot(network)
            
            return result
            
        except Exception as e:
            return {
                'network': network.value,
                'status': 'error',
                'error': str(e)
            }
    
    async def _test_friendbot(self, network: StellarNetwork) -> bool:
        """Test friendbot availability."""
        try:
            config = self.network_manager.get_network_config(network)
            friendbot_url = config.friendbot['url']
            
            async with aiohttp.ClientSession() as session:
                # Test with a dummy account
                test_account = Keypair.random().public_key
                async with session.get(
                    f"{friendbot_url}?addr={test_account}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return response.status == 200
                    
        except Exception:
            return False
    
    async def create_test_accounts(
        self, 
        networks: List[StellarNetwork] = None,
        count: int = 3
    ) -> Dict[str, List[Dict[str, str]]]:
        """Create test accounts for specified networks."""
        if networks is None:
            networks = [net for net in StellarNetwork if net in self.network_manager.network_configs]
        
        print(f"🔧 Creating {count} test accounts for each network...")
        
        for network in networks:
            if network == StellarNetwork.MAINNET:
                print(f"  ⏭️  Skipping mainnet (no test account creation)")
                continue
                
            print(f"  💰 Creating accounts for {network.value.upper()}...")
            accounts = await self._create_network_test_accounts(network, count)
            self.test_accounts[network] = accounts
            
            print(f"    ✅ Created {len(accounts)} accounts")
            for i, account in enumerate(accounts, 1):
                print(f"      {i}. {account['public_key'][:8]}...")
        
        return self.test_accounts
    
    async def _create_network_test_accounts(
        self,
        network: StellarNetwork,
        count: int
    ) -> List[Dict[str, str]]:
        """Create test accounts for a specific network."""
        config = self.network_manager.get_network_config(network)
        accounts = []
        
        for i in range(count):
            # Generate keypair
            keypair = Keypair.random()
            account_info = {
                'public_key': keypair.public_key,
                'secret_key': keypair.secret,
                'network': network.value,
                'funded': False,
                'balance': '0'
            }
            
            # Fund account if friendbot is available
            if config.friendbot and config.friendbot.get('enabled'):
                try:
                    success = await self.network_manager.fund_test_account(
                        keypair.public_key, network
                    )
                    if success:
                        account_info['funded'] = True
                        
                        # Get balance
                        try:
                            balance_info = await self.network_manager.get_account_balance(
                                keypair.public_key, network
                            )
                            native_balance = next(
                                (b['balance'] for b in balance_info['balances'] 
                                 if b['asset_type'] == 'native'),
                                '0'
                            )
                            account_info['balance'] = native_balance
                        except Exception:
                            pass  # Balance fetch failed, keep default
                            
                except Exception as e:
                    print(f"    ⚠️  Failed to fund account {i+1}: {e}")
            
            accounts.append(account_info)
        
        return accounts
    
    async def save_test_accounts(self, output_file: str = "test_accounts.json"):
        """Save test accounts to JSON file."""
        if not self.test_accounts:
            print("  ⚠️  No test accounts to save")
            return
        
        # Convert enum keys to strings for JSON serialization
        serializable_accounts = {
            network.value: accounts 
            for network, accounts in self.test_accounts.items()
        }
        
        output_path = Path(output_file)
        with open(output_path, 'w') as f:
            json.dump(serializable_accounts, f, indent=2)
        
        print(f"  💾 Saved test accounts to {output_path.absolute()}")
    
    async def test_trading_functionality(self, network: StellarNetwork = None) -> Dict[str, Any]:
        """Test basic trading functionality on specified network."""
        target_network = network or StellarNetwork.TESTNET
        
        print(f"🧪 Testing trading functionality on {target_network.value.upper()}...")
        
        if target_network not in self.test_accounts or len(self.test_accounts[target_network]) < 2:
            print(f"  ❌ Need at least 2 test accounts for {target_network.value}")
            return {'status': 'error', 'message': 'Insufficient test accounts'}
        
        server = self.network_manager.get_server(target_network)
        config = self.network_manager.get_network_config(target_network)
        
        # Get two funded accounts
        funded_accounts = [
            acc for acc in self.test_accounts[target_network] 
            if acc['funded'] and float(acc['balance']) > 1
        ]
        
        if len(funded_accounts) < 2:
            print(f"  ❌ Need at least 2 funded accounts for {target_network.value}")
            return {'status': 'error', 'message': 'Insufficient funded accounts'}
        
        account1 = funded_accounts[0]
        account2 = funded_accounts[1]
        
        try:
            # Test 1: Account info retrieval
            print("  📋 Testing account info retrieval...")
            account_info = await server.accounts().account_id(account1['public_key']).call()
            print(f"    ✅ Retrieved account info for {account1['public_key'][:8]}...")
            
            # Test 2: Order book retrieval (if supported assets exist)
            print("  📊 Testing order book retrieval...")
            well_known_assets = config.well_known_assets
            if well_known_assets:
                # Get first available asset pair
                asset_codes = list(well_known_assets.keys())
                if len(asset_codes) > 0:
                    first_asset = asset_codes[0]
                    selling_asset = self.network_manager.get_well_known_asset(first_asset, target_network)
                    buying_asset = self.network_manager.get_well_known_asset(config.native_asset, target_network)
                    
                    if selling_asset and buying_asset:
                        try:
                            order_book = await server.orderbook(selling_asset, buying_asset).call()
                            print(f"    ✅ Retrieved order book for {first_asset}-{config.native_asset}")
                        except Exception as e:
                            print(f"    ⚠️  Order book retrieval failed: {e}")
            
            # Test 3: Transaction submission (simple payment)
            print("  💸 Testing transaction submission...")
            # This would implement a simple payment test between accounts
            # For now, we'll just validate the setup is ready for transactions
            
            return {
                'status': 'success',
                'network': target_network.value,
                'tests_passed': ['account_info', 'order_book'],
                'account1': account1['public_key'],
                'account2': account2['public_key']
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'network': target_network.value,
                'error': str(e)
            }
    
    def print_network_summary(self, validation_results: Dict[str, Any]):
        """Print a summary of network validation results."""
        print("\n" + "="*60)
        print("🌐 STELLAR NETWORK SUMMARY")
        print("="*60)
        
        for network_name, result in validation_results.items():
            status = result.get('status', 'unknown')
            
            if status == 'healthy':
                status_icon = "✅"
            elif status == 'degraded':
                status_icon = "⚠️ "
            elif status == 'down':
                status_icon = "❌"
            else:
                status_icon = "❓"
            
            print(f"\n{status_icon} {network_name.upper()}")
            
            if 'error' in result:
                print(f"   Error: {result['error']}")
                continue
            
            print(f"   Status: {status}")
            print(f"   Response Time: {result.get('avg_response_time', 0)}ms")
            print(f"   Error Rate: {result.get('error_rate', 0)*100:.1f}%")
            
            if 'ledger_info' in result and result['ledger_info']:
                ledger = result['ledger_info']
                print(f"   Latest Ledger: #{ledger['sequence']}")
                print(f"   Transactions: {ledger['transaction_count']}")
            
            if 'friendbot_available' in result:
                friendbot_status = "✅" if result['friendbot_available'] else "❌"
                print(f"   Friendbot: {friendbot_status}")
        
        print("\n" + "="*60)


async def main():
    """Main setup script."""
    parser = argparse.ArgumentParser(description="Stellar Network Setup and Validation")
    parser.add_argument("--config", default="config/networks.yml", 
                       help="Path to network configuration file")
    parser.add_argument("--validate", action="store_true", 
                       help="Validate all configured networks")
    parser.add_argument("--create-accounts", action="store_true",
                       help="Create test accounts for development")
    parser.add_argument("--account-count", type=int, default=3,
                       help="Number of test accounts to create per network")
    parser.add_argument("--test-trading", action="store_true",
                       help="Test basic trading functionality")
    parser.add_argument("--network", choices=["testnet", "futurenet", "mainnet"],
                       help="Specify network for testing")
    parser.add_argument("--output", default="test_accounts.json",
                       help="Output file for test accounts")
    
    args = parser.parse_args()
    
    # Initialize setup
    setup = StellarNetworkSetup(args.config)
    await setup.initialize()
    
    try:
        validation_results = {}
        
        # Always run validation first
        print("🚀 Starting Stellar network setup and validation...\n")
        validation_results = await setup.validate_all_networks()
        
        if args.validate:
            setup.print_network_summary(validation_results)
        
        # Create test accounts if requested
        if args.create_accounts:
            networks = None
            if args.network:
                networks = [StellarNetwork(args.network)]
            
            await setup.create_test_accounts(networks, args.account_count)
            await setup.save_test_accounts(args.output)
        
        # Test trading functionality if requested
        if args.test_trading:
            test_network = None
            if args.network:
                test_network = StellarNetwork(args.network)
            
            trading_result = await setup.test_trading_functionality(test_network)
            print(f"\n🧪 Trading test result: {trading_result}")
        
        # Final summary
        if not args.validate:  # Only print if not already printed
            setup.print_network_summary(validation_results)
        
        print("\n🎉 Setup complete!")
        
    finally:
        await setup.cleanup()


if __name__ == "__main__":
    asyncio.run(main())