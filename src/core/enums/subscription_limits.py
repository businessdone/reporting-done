"""Reports-specific subscription limits.

This module provides OCR page limits for each subscription tier.
These are reports-specific extensions to the bd-core SubscriptionTier enum.
"""

from businessdone_core.enums import SubscriptionTier


OCR_PAGE_LIMITS: dict[SubscriptionTier, int] = {
    SubscriptionTier.FREE: 10,
    SubscriptionTier.TIER_1: 300,
    SubscriptionTier.TIER_2: 1000,
    SubscriptionTier.TIER_3: 3500,
    SubscriptionTier.TIER_4: 14000,
}


def get_ocr_page_limit(tier: SubscriptionTier) -> int:
    """Get monthly OCR page limit for the subscription tier.

    Args:
        tier: The subscription tier to get the limit for.

    Returns:
        The monthly OCR page limit for the given tier.

    Raises:
        KeyError: If the tier is not found in the limits mapping.
    """
    return OCR_PAGE_LIMITS[tier]
