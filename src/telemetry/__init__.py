"""
Privacy-preserving telemetry module for PM Agent.

This module provides telemetry collection capabilities that respect user privacy
by anonymizing and aggregating data before transmission. It includes:

- Anonymous health metrics collection
- User consent management
- Data encryption and secure transmission
- Local-first processing and aggregation

All telemetry is opt-in and users have full control over what data is shared.
"""

from .client import TelemetryClient
from .anonymizer import DataAnonymizer
from .consent import ConsentManager

__all__ = [
    'TelemetryClient',
    'DataAnonymizer', 
    'ConsentManager'
]