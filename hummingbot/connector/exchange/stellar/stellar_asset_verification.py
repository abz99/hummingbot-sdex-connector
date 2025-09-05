"""
Stellar Asset Verification
Runtime verification of assets against stellar.toml files and multiple asset directories.
"""

import asyncio
import aiohttp
import hashlib
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
import toml
from urllib.parse import urljoin, urlparse

from .stellar_logging import get_stellar_logger, LogCategory, with_correlation_id
from .stellar_metrics import get_stellar_metrics


class VerificationStatus(Enum):
    """Asset verification status."""
    VERIFIED = auto()
    NOT_VERIFIED = auto()
    VERIFICATION_FAILED = auto()
    PENDING = auto()
    EXPIRED = auto()


class AssetRisk(Enum):
    """Asset risk levels."""
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass
class AssetMetadata:
    """Asset metadata from stellar.toml."""
    code: str
    issuer: str
    domain: str
    name: Optional[str] = None
    desc: Optional[str] = None
    image: Optional[str] = None
    conditions: Optional[str] = None
    is_anchor_asset: bool = False
    anchor_asset_type: Optional[str] = None
    anchor_asset: Optional[str] = None
    redemption_instructions: Optional[str] = None
    collateral_addresses: List[str] = field(default_factory=list)
    collateral_address_messages: List[str] = field(default_factory=list)
    collateral_address_signatures: List[str] = field(default_factory=list)
    status: str = "live"
    display_decimals: Optional[int] = None
    regulated: bool = False
    approval_server: Optional[str] = None
    approval_criteria: Optional[str] = None
    kyc_required: bool = False
    aml_required: bool = False


@dataclass
class VerificationResult:
    """Result of asset verification."""
    asset_code: str
    issuer: str
    domain: str
    status: VerificationStatus
    risk_level: AssetRisk
    metadata: Optional[AssetMetadata] = None
    verification_time: datetime = field(default_factory=datetime.utcnow)
    expiry_time: Optional[datetime] = None
    error_message: Optional[str] = None
    toml_url: Optional[str] = None
    toml_hash: Optional[str] = None
    compliance_flags: Dict[str, bool] = field(default_factory=dict)


@dataclass
class AssetDirectory:
    """Asset directory configuration."""
    name: str
    base_url: str
    priority: int = 1
    requires_auth: bool = False
    auth_token: Optional[str] = None
    rate_limit: int = 10  # requests per second


class StellarAssetVerifier:
    """Verifies Stellar assets against their stellar.toml files."""
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self.logger = get_stellar_logger()
        self.metrics = get_stellar_metrics()
        self.session = session
        self._session_owned = session is None
        
        # Verification cache
        self._verification_cache: Dict[str, VerificationResult] = {}
        self._cache_expiry = timedelta(hours=24)  # Cache for 24 hours
        
        # Rate limiting
        self._rate_limits: Dict[str, List[float]] = {}
        
        # Asset directories
        self.asset_directories: List[AssetDirectory] = []
        
    async def __aenter__(self):
        """Async context manager entry."""
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={'User-Agent': 'StellarConnector/3.0.0'}
            )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session_owned and self.session:
            await self.session.close()
    
    def add_asset_directory(self, directory: AssetDirectory):
        """Add an asset directory for verification."""
        self.asset_directories.append(directory)
        self.asset_directories.sort(key=lambda x: x.priority)
    
    async def verify_asset(
        self, 
        asset_code: str, 
        issuer: str, 
        expected_domain: Optional[str] = None,
        force_refresh: bool = False
    ) -> VerificationResult:
        """
        Verify an asset against its stellar.toml file.
        
        Args:
            asset_code: Asset code (e.g., 'USDC')
            issuer: Asset issuer public key
            expected_domain: Expected domain for additional verification
            force_refresh: Force refresh of cached data
            
        Returns:
            VerificationResult with verification status and metadata
        """
        cache_key = f"{asset_code}:{issuer}"
        
        # Check cache first
        if not force_refresh and cache_key in self._verification_cache:
            cached = self._verification_cache[cache_key]
            if datetime.utcnow() < (cached.verification_time + self._cache_expiry):
                return cached
        
        with with_correlation_id() as logger:
            logger.info(
                f"Starting asset verification: {asset_code} ({issuer[:8]}...)",
                category=LogCategory.SECURITY,
                asset_code=asset_code,
                issuer=issuer,
                expected_domain=expected_domain
            )
            
            start_time = datetime.utcnow()
            
            try:
                # Get account info to find home domain
                domain = await self._get_asset_domain(issuer)
                if not domain:
                    return self._create_failed_result(
                        asset_code, issuer, None,
                        "No home domain found in issuer account"
                    )
                
                # Verify expected domain if provided
                if expected_domain and domain != expected_domain:
                    return self._create_failed_result(
                        asset_code, issuer, domain,
                        f"Domain mismatch: expected {expected_domain}, found {domain}"
                    )
                
                # Fetch and parse stellar.toml
                toml_url, toml_content, toml_hash = await self._fetch_stellar_toml(domain)
                if not toml_content:
                    return self._create_failed_result(
                        asset_code, issuer, domain,
                        f"Failed to fetch stellar.toml from {domain}"
                    )
                
                # Parse TOML content
                parsed_toml = await self._parse_stellar_toml(toml_content)
                if not parsed_toml:
                    return self._create_failed_result(
                        asset_code, issuer, domain,
                        "Failed to parse stellar.toml content"
                    )
                
                # Find asset in TOML
                asset_metadata = await self._find_asset_in_toml(
                    parsed_toml, asset_code, issuer
                )
                
                if not asset_metadata:
                    return self._create_failed_result(
                        asset_code, issuer, domain,
                        f"Asset {asset_code} not found in stellar.toml"
                    )
                
                # Additional verification from asset directories
                directory_info = await self._verify_with_directories(asset_code, issuer)
                
                # Determine risk level
                risk_level = self._assess_risk_level(asset_metadata, directory_info)
                
                # Create successful result
                result = VerificationResult(
                    asset_code=asset_code,
                    issuer=issuer,
                    domain=domain,
                    status=VerificationStatus.VERIFIED,
                    risk_level=risk_level,
                    metadata=asset_metadata,
                    toml_url=toml_url,
                    toml_hash=toml_hash,
                    compliance_flags=self._check_compliance(asset_metadata),
                    expiry_time=datetime.utcnow() + self._cache_expiry
                )
                
                # Cache the result
                self._verification_cache[cache_key] = result
                
                # Log success
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.info(
                    f"Asset verification successful: {asset_code}",
                    category=LogCategory.SECURITY,
                    duration_seconds=duration,
                    domain=domain,
                    risk_level=risk_level.name
                )
                
                # Record metrics
                self.metrics.record_network_request('asset_verification', 'stellar_toml', 'success', duration)
                
                return result
                
            except Exception as e:
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.error(
                    f"Asset verification failed: {asset_code}",
                    category=LogCategory.SECURITY,
                    exception=e,
                    duration_seconds=duration
                )
                
                # Record metrics
                self.metrics.record_network_request('asset_verification', 'stellar_toml', 'error', duration)
                
                return self._create_failed_result(
                    asset_code, issuer, None,
                    f"Verification error: {str(e)}"
                )
    
    async def verify_multiple_assets(
        self, 
        assets: List[Tuple[str, str]], 
        max_concurrent: int = 10
    ) -> Dict[str, VerificationResult]:
        """
        Verify multiple assets concurrently.
        
        Args:
            assets: List of (asset_code, issuer) tuples
            max_concurrent: Maximum concurrent verifications
            
        Returns:
            Dictionary mapping asset keys to verification results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def verify_single(asset_code: str, issuer: str) -> Tuple[str, VerificationResult]:
            async with semaphore:
                result = await self.verify_asset(asset_code, issuer)
                return f"{asset_code}:{issuer}", result
        
        tasks = [verify_single(code, issuer) for code, issuer in assets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        verified_assets = {}
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(
                    "Error in batch asset verification",
                    category=LogCategory.SECURITY,
                    exception=result
                )
                continue
            
            key, verification_result = result
            verified_assets[key] = verification_result
        
        return verified_assets
    
    async def _get_asset_domain(self, issuer: str) -> Optional[str]:
        """Get the home domain for an asset issuer."""
        # This would typically query the Stellar network
        # For now, return None to indicate domain lookup needed
        # In a real implementation, this would use the Stellar SDK
        return None
    
    async def _fetch_stellar_toml(self, domain: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Fetch stellar.toml file from domain.
        
        Returns:
            Tuple of (url, content, hash)
        """
        toml_urls = [
            f"https://{domain}/.well-known/stellar.toml",
            f"https://www.{domain}/.well-known/stellar.toml",
            f"http://{domain}/.well-known/stellar.toml",  # Fallback
        ]
        
        for url in toml_urls:
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        content_hash = hashlib.sha256(content.encode()).hexdigest()
                        return url, content, content_hash
            except Exception as e:
                self.logger.debug(
                    f"Failed to fetch stellar.toml from {url}",
                    category=LogCategory.SECURITY,
                    exception=e
                )
                continue
        
        return None, None, None
    
    async def _parse_stellar_toml(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse stellar.toml content."""
        try:
            return toml.loads(content)
        except Exception as e:
            self.logger.error(
                "Failed to parse stellar.toml",
                category=LogCategory.SECURITY,
                exception=e
            )
            return None
    
    async def _find_asset_in_toml(
        self, 
        parsed_toml: Dict[str, Any], 
        asset_code: str, 
        issuer: str
    ) -> Optional[AssetMetadata]:
        """Find asset information in parsed stellar.toml."""
        currencies = parsed_toml.get('CURRENCIES', [])
        
        for currency in currencies:
            if (currency.get('code') == asset_code and 
                currency.get('issuer') == issuer):
                
                return AssetMetadata(
                    code=asset_code,
                    issuer=issuer,
                    domain=parsed_toml.get('NETWORK_PASSPHRASE', ''),
                    name=currency.get('name'),
                    desc=currency.get('desc'),
                    image=currency.get('image'),
                    conditions=currency.get('conditions'),
                    is_anchor_asset=currency.get('is_anchor_asset', False),
                    anchor_asset_type=currency.get('anchor_asset_type'),
                    anchor_asset=currency.get('anchor_asset'),
                    redemption_instructions=currency.get('redemption_instructions'),
                    status=currency.get('status', 'live'),
                    display_decimals=currency.get('display_decimals'),
                    regulated=currency.get('regulated', False),
                    approval_server=currency.get('approval_server'),
                    approval_criteria=currency.get('approval_criteria'),
                    kyc_required='kyc' in currency.get('approval_criteria', '').lower(),
                    aml_required='aml' in currency.get('approval_criteria', '').lower(),
                )
        
        return None
    
    async def _verify_with_directories(
        self, 
        asset_code: str, 
        issuer: str
    ) -> Dict[str, Any]:
        """Verify asset with external asset directories."""
        directory_results = {}
        
        for directory in self.asset_directories:
            try:
                # Rate limiting check
                if not await self._check_rate_limit(directory.name, directory.rate_limit):
                    self.logger.warning(
                        f"Rate limit exceeded for directory {directory.name}",
                        category=LogCategory.SECURITY
                    )
                    continue
                
                # Query directory
                result = await self._query_asset_directory(directory, asset_code, issuer)
                if result:
                    directory_results[directory.name] = result
                    
            except Exception as e:
                self.logger.error(
                    f"Error querying asset directory {directory.name}",
                    category=LogCategory.SECURITY,
                    exception=e
                )
        
        return directory_results
    
    async def _query_asset_directory(
        self, 
        directory: AssetDirectory, 
        asset_code: str, 
        issuer: str
    ) -> Optional[Dict[str, Any]]:
        """Query a specific asset directory."""
        # This would implement actual directory queries
        # Each directory would have its own API format
        return None
    
    async def _check_rate_limit(self, directory_name: str, limit: int) -> bool:
        """Check rate limit for a directory."""
        now = asyncio.get_event_loop().time()
        
        if directory_name not in self._rate_limits:
            self._rate_limits[directory_name] = []
        
        # Clean old timestamps
        cutoff = now - 1.0  # 1 second window
        self._rate_limits[directory_name] = [
            ts for ts in self._rate_limits[directory_name] if ts > cutoff
        ]
        
        # Check limit
        if len(self._rate_limits[directory_name]) >= limit:
            return False
        
        # Add current timestamp
        self._rate_limits[directory_name].append(now)
        return True
    
    def _assess_risk_level(
        self, 
        metadata: AssetMetadata, 
        directory_info: Dict[str, Any]
    ) -> AssetRisk:
        """Assess risk level based on asset metadata and directory information."""
        risk_score = 0
        
        # Basic metadata checks
        if not metadata.desc:
            risk_score += 1
        if not metadata.image:
            risk_score += 1
        if metadata.status != 'live':
            risk_score += 3
        if metadata.regulated and not metadata.approval_server:
            risk_score += 2
        
        # KYC/AML requirements
        if metadata.kyc_required:
            risk_score += 1  # Actually lowers risk but adds complexity
        if metadata.aml_required:
            risk_score += 1
        
        # Directory verification
        if not directory_info:
            risk_score += 2
        elif len(directory_info) < 2:
            risk_score += 1
        
        # Determine risk level
        if risk_score <= 2:
            return AssetRisk.LOW
        elif risk_score <= 4:
            return AssetRisk.MEDIUM
        elif risk_score <= 6:
            return AssetRisk.HIGH
        else:
            return AssetRisk.CRITICAL
    
    def _check_compliance(self, metadata: AssetMetadata) -> Dict[str, bool]:
        """Check compliance flags for the asset."""
        return {
            'has_description': bool(metadata.desc),
            'has_image': bool(metadata.image),
            'is_live': metadata.status == 'live',
            'is_regulated': metadata.regulated,
            'has_approval_server': bool(metadata.approval_server),
            'kyc_required': metadata.kyc_required,
            'aml_required': metadata.aml_required,
            'has_redemption_instructions': bool(metadata.redemption_instructions),
        }
    
    def _create_failed_result(
        self, 
        asset_code: str, 
        issuer: str, 
        domain: Optional[str], 
        error_message: str
    ) -> VerificationResult:
        """Create a failed verification result."""
        return VerificationResult(
            asset_code=asset_code,
            issuer=issuer,
            domain=domain or "unknown",
            status=VerificationStatus.VERIFICATION_FAILED,
            risk_level=AssetRisk.CRITICAL,
            error_message=error_message
        )
    
    def get_cached_verification(self, asset_code: str, issuer: str) -> Optional[VerificationResult]:
        """Get cached verification result if available and not expired."""
        cache_key = f"{asset_code}:{issuer}"
        if cache_key in self._verification_cache:
            cached = self._verification_cache[cache_key]
            if datetime.utcnow() < (cached.verification_time + self._cache_expiry):
                return cached
        return None
    
    def clear_cache(self, asset_code: Optional[str] = None, issuer: Optional[str] = None):
        """Clear verification cache."""
        if asset_code and issuer:
            cache_key = f"{asset_code}:{issuer}"
            self._verification_cache.pop(cache_key, None)
        else:
            self._verification_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self._verification_cache)
        expired_entries = sum(
            1 for result in self._verification_cache.values()
            if datetime.utcnow() >= (result.verification_time + self._cache_expiry)
        )
        
        return {
            'total_entries': total_entries,
            'expired_entries': expired_entries,
            'active_entries': total_entries - expired_entries,
            'cache_hit_ratio': getattr(self, '_cache_hits', 0) / max(getattr(self, '_cache_requests', 1), 1)
        }


# Default asset directories
DEFAULT_ASSET_DIRECTORIES = [
    AssetDirectory(
        name="StellarTerm",
        base_url="https://stellarterm.com/directory/",
        priority=1
    ),
    AssetDirectory(
        name="StellarExpert",
        base_url="https://stellar.expert/explorer/public/asset/",
        priority=2
    ),
    AssetDirectory(
        name="LOBSTR",
        base_url="https://lobstr.co/assets/",
        priority=3
    ),
]