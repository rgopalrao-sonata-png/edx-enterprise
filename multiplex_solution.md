# Multiplex Subscription Licenses - Solution Architecture

**Date:** March 26, 2026  
**Version:** 1.0  
**Status:** Proposed Architecture  
**Architect:** Solution Design based on edX Enterprise Platform Analysis  

**Related Documents:**
- [Requirements (test.txt)](test.txt)
- [Current Process Analysis](current-license-selection-process-code-walkthrough.md)
- [Implementation RFC](multiplex-subscription-licenses-rfc.md)

---

## Executive Summary

### Problem Statement
The edX enterprise platform currently **collapses multiple active subscription licenses to a single license** at 4 critical bottlenecks, preventing learners from accessing courses they're entitled to through alternative licenses. This blocks Knotion's "Learning Pathways" feature and limits multi-catalog enterprise use cases.

### Architectural Root Cause
**Single Responsibility Violation:** The system conflates two distinct concerns:
1. **Data retrieval** (getting all licenses) 
2. **Selection logic** (choosing which license applies to a specific course)

Current architecture performs selection too early (at data layer), losing information needed for downstream course-level decisions.

### Proposed Solution
**Separation of Concerns Pattern:** 
- **Data layer** provides complete license collections (no selection)
- **Business logic layer** performs per-course license matching (deferred selection)
- **Backward compatibility layer** maintains legacy singular fields during migration

### Success Metrics
- ✅ Learners with 3 licenses can access courses from all 3 catalogs
- ✅ Default auto-enrollment works across all assigned catalogs
- ✅ Support Tool shows accurate activation status for all licenses
- ✅ X license assignments = X activation emails
- ✅ Zero disruption to existing single-license learners
- ✅ <5ms latency increase for multi-license evaluation

---

## Table of Contents

1. [Architectural Principles](#architectural-principles)
2. [Solution Overview](#solution-overview)
3. [Detailed Design](#detailed-design)
4. [Implementation Strategy](#implementation-strategy)
5. [Migration Plan](#migration-plan)
6. [Testing Strategy](#testing-strategy)
7. [Monitoring & Observability](#monitoring--observability)
8. [Risk Management](#risk-management)
9. [Future Enhancements](#future-enhancements)

---

## Architectural Principles

### 1. Collection-First Design
**Principle:** Always preserve the complete dataset until the last responsible moment.

**Why:** Information loss (reducing N licenses to 1) cannot be recovered downstream. The layer that needs to make the decision (course page) should have all the data (all licenses).

**Application:**
```python
# ❌ BAD: Early selection loses information
def get_user_license(user_id):
    licenses = fetch_all_licenses(user_id)
    return licenses[0]  # Information loss!

# ✅ GOOD: Preserve collection, defer selection
def get_user_licenses(user_id):
    return fetch_all_licenses(user_id)  # Complete data

def get_applicable_license_for_course(licenses, course_id):
    return find_best_match(licenses, course_id)  # Context-aware selection
```

### 2. Single Responsibility Principle
**Principle:** Each layer has one clear responsibility.

**Application:**
- **License Manager:** Persist and return license records (no business logic)
- **BFF:** Fetch, transform, enrich data for frontend (no selection)
- **MFE:** Display data, handle user interaction (selection at course context)
- **Business Logic:** Determine applicability rules (separate, testable)

### 3. Backward Compatibility
**Principle:** New behavior must not break existing integrations.

**Application:**
- Maintain deprecated singular fields alongside new plural fields
- Use feature flags for gradual rollout
- Version the response schema explicitly
- Provide migration window (6 months minimum)

### 4. Fail-Safe Defaults
**Principle:** When in doubt, default to existing behavior.

**Application:**
```python
# Feature flag OFF → legacy single-license behavior
# Feature flag ON → new multi-license behavior
# Flag read failure → defaults to OFF (safe)
```

### 5. Observable by Design
**Principle:** Build monitoring, logging, and debugging into the architecture.

**Application:**
- Emit metrics at each decision point
- Log license selection rationale
- Trace requests across services
- Dashboard for multi-license adoption

### 6. Test-First Development
**Principle:** Tests define behavior before implementation (per test.txt).

**Application:**
- Write integration tests for multi-license scenarios first
- Use test data builder pattern for license combinations
- Validate both happy path and edge cases
- Performance benchmarks as tests

---

## Solution Overview

### High-Level Architecture

```mermaid
graph TB
    subgraph "Current State (Bottlenecks)"
        C1[License Manager<br/>Returns ALL]
        C2[BFF<br/>Selects FIRST ❌]
        C3[MFE<br/>Selects FIRST ❌]
        C4[Course Page<br/>Uses FIRST ❌]
        
        C1 -->|[A,B,C]| C2
        C2 -->|A only| C3
        C3 -->|A only| C4
    end
    
    subgraph "Target State (Collection-First)"
        T1[License Manager<br/>Returns ALL]
        T2[BFF<br/>Preserves ALL ✓]
        T3[MFE<br/>Receives ALL ✓]
        T4[Course Page<br/>Matches BEST ✓]
        
        T1 -->|[A,B,C]| T2
        T2 -->|[A,B,C]| T3
        T3 -->|[A,B,C]| T4
        T4 -->|Select B for<br/>catalog-B course| T4
    end
    
    style C2 fill:#ffcccc
    style C3 fill:#ffcccc
    style C4 fill:#ffcccc
    style T2 fill:#ccffcc
    style T3 fill:#ccffcc
    style T4 fill:#ccffcc
```

### Key Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **Collection-first contract** | Prevents information loss; enables downstream flexibility | Slightly larger payloads (mitigated by compression) |
| **Deterministic selection algorithm** | Predictable behavior; reproducible; debuggable | Requires well-defined precedence rules |
| **Feature flags at BFF + MFE** | Gradual rollout; quick rollback; A/B testing capability | Temporary code complexity during migration |
| **Backward-compatible schema** | Zero disruption to existing integrations | Deprecated fields to maintain for 6 months |
| **Per-course license matching** | Correct entitlements; honors catalog boundaries | Additional computation per course view |
| **No License Manager changes** | Minimal blast radius; faster delivery | BFF must handle business logic |

---

## Detailed Design

### Component 1: License Manager (No Changes)

**Status:** ✅ Already works correctly

**Current Behavior:**
```python
# GET /api/v1/learner-licenses/?enterprise_customer_uuid=X
# Returns ALL licenses (activated, assigned, etc.)
```

**Why No Changes Needed:**
- Already returns complete license collection
- Properly filters by enterprise customer
- Handles active_plans_only, current_plans_only query params
- Supports revoked license inclusion via flag

**Interface Contract:**
```json
{
  "count": 3,
  "results": [
    {
      "uuid": "license-uuid",
      "status": "activated|assigned|revoked",
      "activation_date": "ISO-8601",
      "subscription_plan": {
        "uuid": "plan-uuid",
        "enterprise_catalog_uuid": "catalog-uuid",
        "is_current": true,
        "expiration_date": "YYYY-MM-DD"
      }
    }
  ]
}
```

---

### Component 2: Enterprise Access BFF (Refactored)

#### 2.1 Data Transformation Layer

**Current (Bottleneck #1):**
```python
def _extract_subscription_license(self, subscription_licenses_by_status):
    """Returns FIRST license only ❌"""
    return next((
        license
        for status in [ACTIVATED, ASSIGNED, REVOKED]
        for license in subscription_licenses_by_status.get(status, [])
    ), None)
```

**Proposed (Collection-First):**
```python
class SubscriptionLicenseProcessor:
    """
    Handles subscription license data transformation.
    Preserves collection semantics while maintaining backward compatibility.
    """
    
    def transform_licenses(self, subscription_licenses_by_status, feature_flag_enabled=False):
        """
        Transform license data with collection-first approach.
        
        Args:
            subscription_licenses_by_status: Dict[str, List[License]]
            feature_flag_enabled: bool - ENABLE_MULTI_LICENSE_ENTITLEMENTS_BFF
            
        Returns:
            Dict with both collection and legacy singular fields
        """
        activated_licenses = subscription_licenses_by_status.get(
            LicenseStatuses.ACTIVATED, []
        )
        
        # Sort by current plans first, then expiration date
        sorted_activated = sorted(
            activated_licenses,
            key=lambda lic: (
                not lic.get('subscription_plan', {}).get('is_current', False),
                lic.get('subscription_plan', {}).get('expiration_date', '')
            )
        )
        
        result = {
            # ✅ NEW: Collection-first (canonical)
            'subscription_licenses': sorted_activated,
            'subscription_licenses_by_status': subscription_licenses_by_status,
            
            # ✅ NEW: Pre-computed catalog index for performance
            'licenses_by_catalog': self._index_by_catalog(sorted_activated) if feature_flag_enabled else None,
            
            # ⚠️ DEPRECATED: Backward compatibility (remove in 6 months)
            'subscription_license': sorted_activated[0] if sorted_activated else None,
            'subscription_plan': sorted_activated[0].get('subscription_plan') if sorted_activated else None,
            
            # ✅ NEW: Schema version for client compatibility
            'license_schema_version': 'v2' if feature_flag_enabled else 'v1',
        }
        
        return result
    
    def _index_by_catalog(self, licenses):
        """
        Create catalog UUID → licenses mapping for O(1) lookups.
        
        Returns:
            Dict[str, List[License]] - catalog_uuid to licenses mapping
        """
        catalog_index = {}
        for license in licenses:
            catalog_uuid = license.get('subscription_plan', {}).get('enterprise_catalog_uuid')
            if catalog_uuid:
                if catalog_uuid not in catalog_index:
                    catalog_index[catalog_uuid] = []
                catalog_index[catalog_uuid].append(license)
        return catalog_index
```

#### 2.2 Enrollment Intention Handler

**Current (Bottleneck #2):**
```python
def enroll_in_redeemable_default_enterprise_enrollment_intentions(self):
    """Uses single self.current_activated_license for ALL courses ❌"""
    if not self.current_activated_license:
        return
    
    for enrollment_intention in needs_enrollment_enrollable:
        subscription_catalog = self.current_activated_license.get(
            'subscription_plan', {}
        ).get('enterprise_catalog_uuid')
        
        if subscription_catalog in applicable_catalogs:
            license_uuids_by_course[course_run_key] = self.current_activated_license['uuid']
```

**Proposed (Per-Course Matching):**
```python
class EnrollmentIntentionHandler:
    """
    Handles default enterprise enrollment intentions with multi-license support.
    """
    
    def enroll_in_redeemable_intentions(self, feature_flag_enabled=False):
        """
        Enroll learner in default enterprise courses using best-matching licenses.
        
        Args:
            feature_flag_enabled: bool - ENABLE_MULTI_LICENSE_ENTITLEMENTS_BFF
        """
        enrollment_statuses = self.default_enterprise_enrollment_intentions.get(
            'enrollment_statuses', {}
        )
        needs_enrollment_enrollable = (
            enrollment_statuses.get('needs_enrollment', {}).get('enrollable', [])
        )
        
        if not needs_enrollment_enrollable:
            logger.info(
                "No enrollable default enterprise courses for user %s",
                self.context.lms_user_id
            )
            return
        
        if feature_flag_enabled:
            # ✅ NEW: Multi-license path
            license_course_mappings = self._map_courses_to_licenses(
                needs_enrollment_enrollable
            )
        else:
            # ⚠️ LEGACY: Single-license path (backward compatibility)
            license_course_mappings = self._map_courses_to_single_license(
                needs_enrollment_enrollable
            )
        
        if not license_course_mappings:
            logger.warning(
                "No license matched any enrollable courses for user %s",
                self.context.lms_user_id
            )
            return
        
        self._request_enrollment_realizations(license_course_mappings)
    
    def _map_courses_to_licenses(self, enrollment_intentions):
        """
        ✅ NEW: Map each course to its best-matching license.
        
        Algorithm:
        1. For each course, find ALL licenses whose catalog contains the course
        2. If multiple licenses match, apply deterministic tie-breaker:
           a. Latest expiration date (maximize access window)
           b. Most recent activation date (prefer newer)
           c. UUID lexical order (deterministic fallback)
        
        Returns:
            Dict[str, str] - course_run_key to license_uuid mapping
        """
        activated_licenses = self._get_current_activated_licenses()
        
        if not activated_licenses:
            logger.info("No activated licenses found for multi-license enrollment")
            return {}
        
        # Build catalog → licenses index
        licenses_by_catalog = self._build_catalog_index(activated_licenses)
        
        license_course_mappings = {}
        
        for intention in enrollment_intentions:
            course_run_key = intention['course_run_key']
            applicable_catalogs = intention.get('applicable_enterprise_catalog_uuids', [])
            
            # Find all licenses that cover this course
            matching_licenses = []
            for catalog_uuid in applicable_catalogs:
                matching_licenses.extend(licenses_by_catalog.get(catalog_uuid, []))
            
            if not matching_licenses:
                logger.debug(
                    "No license found for course %s (catalogs: %s)",
                    course_run_key,
                    applicable_catalogs
                )
                continue
            
            # Apply deterministic selection if multiple matches
            best_license = self._select_best_license(matching_licenses)
            license_course_mappings[course_run_key] = best_license['uuid']
            
            logger.info(
                "Mapped course %s to license %s (catalog: %s, expiration: %s)",
                course_run_key,
                best_license['uuid'],
                best_license['subscription_plan']['enterprise_catalog_uuid'],
                best_license['subscription_plan']['expiration_date']
            )
        
        return license_course_mappings
    
    def _select_best_license(self, licenses):
        """
        Deterministic tie-breaker for multiple matching licenses.
        
        Precedence:
        1. Latest expiration_date (longest access window)
        2. Most recent activation_date (prefer newer activations)
        3. UUID lexical order DESC (stable sort)
        
        Returns:
            License - the selected license
        """
        if len(licenses) == 1:
            return licenses[0]
        
        selected = max(
            licenses,
            key=lambda lic: (
                lic.get('subscription_plan', {}).get('expiration_date', ''),
                lic.get('activation_date', ''),
                lic.get('uuid', '')
            )
        )
        
        return selected
    
    def _build_catalog_index(self, licenses):
        """Build catalog_uuid → licenses mapping for efficient lookup"""
        index = {}
        for license in licenses:
            catalog_uuid = license.get('subscription_plan', {}).get('enterprise_catalog_uuid')
            if catalog_uuid:
                if catalog_uuid not in index:
                    index[catalog_uuid] = []
                index[catalog_uuid].append(license)
        return index
    
    def _map_courses_to_single_license(self, enrollment_intentions):
        """⚠️ LEGACY: Backward-compatible single-license mapping"""
        current_license = self.current_activated_license
        
        if not current_license:
            return {}
        
        subscription_catalog = current_license.get(
            'subscription_plan', {}
        ).get('enterprise_catalog_uuid')
        
        mappings = {}
        for intention in enrollment_intentions:
            applicable_catalogs = intention.get('applicable_enterprise_catalog_uuids', [])
            if subscription_catalog in applicable_catalogs:
                mappings[intention['course_run_key']] = current_license['uuid']
        
        return mappings
```

#### 2.3 Response Serializer

**Proposed Schema:**
```python
class LearnerDashboardResponseSerializer(serializers.Serializer):
    """Enhanced BFF response with multi-license support"""
    
    # ✅ NEW: Collection-first fields (canonical)
    subscription_licenses = serializers.ListField(
        child=SubscriptionLicenseSerializer(),
        help_text="Complete list of learner's subscription licenses (CANONICAL)"
    )
    
    subscription_licenses_by_status = serializers.DictField(
        child=serializers.ListField(child=SubscriptionLicenseSerializer()),
        help_text="Licenses grouped by status (activated, assigned, revoked)"
    )
    
    licenses_by_catalog = serializers.DictField(
        child=serializers.ListField(child=SubscriptionLicenseSerializer()),
        required=False,
        help_text="Pre-computed catalog_uuid → licenses mapping (optional, performance optimization)"
    )
    
    # ✅ NEW: Version indicator
    license_schema_version = serializers.CharField(
        help_text="Schema version: 'v1' (single license) or 'v2' (multi-license)"
    )
    
    # ⚠️ DEPRECATED: Maintain for backward compatibility (6 months)
    subscription_license = SubscriptionLicenseSerializer(
        required=False,
        help_text="DEPRECATED: Single license for backward compatibility. Use subscription_licenses instead."
    )
    
    subscription_plan = SubscriptionPlanSerializer(
        required=False,
        help_text="DEPRECATED: Plan of single license. Use subscription_licenses instead."
    )
```

---

### Component 3: Learner Portal MFE (Refactored)

#### 3.1 Data Service Layer

**Current (Bottleneck #3):**
```javascript
export function transformSubscriptionsData({ subscriptionLicenses }) {
  // ... grouping logic ...
  
  // ❌ Extract first license only
  const applicableSubscriptionLicense = Object.values(
    subscriptionLicensesByStatus
  ).flat()[0];
  
  subscriptionsData.subscriptionLicense = applicableSubscriptionLicense;
}
```

**Proposed (Collection Preservation):**
```javascript
/**
 * Transform subscription license data with collection-first approach.
 * 
 * @param {Object} params
 * @param {SubscriptionLicense[]} params.subscriptionLicenses - All licenses
 * @param {CustomerAgreement} params.customerAgreement
 * @param {string} params.licenseSchemaVersion - 'v1' or 'v2'
 * @returns {Object} Transformed subscription data
 */
export function transformSubscriptionsData({
  subscriptionLicenses,
  customerAgreement,
  licenseSchemaVersion = 'v1',
}) {
  const { baseSubscriptionsData } = getBaseSubscriptionsData();
  const subscriptionsData = { ...baseSubscriptionsData };

  // ✅ ALWAYS preserve complete collection
  if (subscriptionLicenses) {
    subscriptionsData.subscriptionLicenses = subscriptionLicenses;
  }
  
  if (customerAgreement) {
    subscriptionsData.customerAgreement = customerAgreement;
  }

  subscriptionsData.showExpirationNotifications = !(
    customerAgreement?.disableExpirationNotifications
    || customerAgreement?.hasCustomLicenseExpirationMessagingV2
  );

  // Sort licenses: current plans first, then by expiration date
  subscriptionsData.subscriptionLicenses = [...subscriptionLicenses].sort((a, b) => {
    const aIsCurrent = a.subscriptionPlan.isCurrent;
    const bIsCurrent = b.subscriptionPlan.isCurrent;
    
    if (aIsCurrent !== bIsCurrent) {
      return aIsCurrent ? -1 : 1;
    }
    
    // Both current or both not current - sort by expiration date
    const aExp = new Date(a.subscriptionPlan.expirationDate);
    const bExp = new Date(b.subscriptionPlan.expirationDate);
    return bExp - aExp; // Latest expiration first
  });

  // Group licenses by status
  subscriptionsData.subscriptionLicenses.forEach((license) => {
    if (license.status === LICENSE_STATUS.UNASSIGNED) {
      return;
    }
    const updatedLicensesByStatus = addLicenseToSubscriptionLicensesByStatus({
      subscriptionLicensesByStatus: subscriptionsData.subscriptionLicensesByStatus,
      subscriptionLicense: license,
    });
    subscriptionsData.subscriptionLicensesByStatus = updatedLicensesByStatus;
  });

  // ✅ NEW: Create catalog index for O(1) course-to-license lookups
  subscriptionsData.licensesByCatalog = buildCatalogIndex(
    subscriptionsData.subscriptionLicenses
  );
  
  // ✅ NEW: Store schema version
  subscriptionsData.licenseSchemaVersion = licenseSchemaVersion;

  // ⚠️ BACKWARD COMPATIBILITY: Maintain singular field for legacy consumers
  // Only used when feature flag is OFF
  const applicableSubscriptionLicense = Object.values(
    subscriptionsData.subscriptionLicensesByStatus
  ).flat()[0];
  
  if (applicableSubscriptionLicense) {
    subscriptionsData.subscriptionLicense = applicableSubscriptionLicense;
    subscriptionsData.subscriptionPlan = applicableSubscriptionLicense.subscriptionPlan;
  }

  return subscriptionsData;
}

/**
 * ✅ NEW: Build catalog UUID → licenses index for efficient lookups
 * 
 * @param {SubscriptionLicense[]} licenses
 * @returns {Object.<string, SubscriptionLicense[]>}
 */
function buildCatalogIndex(licenses) {
  const index = {};
  
  licenses.forEach((license) => {
    if (license.status !== LICENSE_STATUS.ACTIVATED) {
      return; // Only index activated licenses
    }
    
    if (!license.subscriptionPlan?.isCurrent) {
      return; // Only index current plans
    }
    
    const catalogUuid = license.subscriptionPlan.enterpriseCatalogUuid;
    if (!catalogUuid) {
      return;
    }
    
    if (!index[catalogUuid]) {
      index[catalogUuid] = [];
    }
    index[catalogUuid].push(license);
  });
  
  return index;
}
```

#### 3.2 License Matching Utilities

**Current (Bottleneck #4):**
```javascript
export function determineSubscriptionLicenseApplicable(subscriptionLicense, catalogsWithCourse) {
  return (
    subscriptionLicense?.status === LICENSE_STATUS.ACTIVATED
    && subscriptionLicense?.subscriptionPlan.isCurrent
    && catalogsWithCourse.includes(subscriptionLicense?.subscriptionPlan.enterpriseCatalogUuid)
  );
}
```

**Proposed (Multi-License Matching):**
```javascript
/**
 * ✅ NEW: Find all licenses applicable to a specific course.
 * 
 * @param {SubscriptionLicense[]} subscriptionLicenses - All learner licenses
 * @param {string[]} catalogsWithCourse - Catalog UUIDs containing the course
 * @returns {SubscriptionLicense[]} Applicable licenses
 */
export function getApplicableLicensesForCourse(subscriptionLicenses, catalogsWithCourse) {
  if (!subscriptionLicenses || !Array.isArray(subscriptionLicenses)) {
    return [];
  }
  
  if (!catalogsWithCourse || catalogsWithCourse.length === 0) {
    return [];
  }
  
  return subscriptionLicenses.filter(license => (
    // Must be activated
    license?.status === LICENSE_STATUS.ACTIVATED
    // Plan must be current (not expired)
    && license?.subscriptionPlan?.isCurrent === true
    // License's catalog must contain this course
    && catalogsWithCourse.includes(license?.subscriptionPlan?.enterpriseCatalogUuid)
  ));
}

/**
 * ✅ NEW: Select the best license from multiple applicable licenses.
 * 
 * Deterministic selection algorithm:
 * 1. Latest expiration date (longest access window)
 * 2. Most recent activation date (prefer newer)
 * 3. UUID descending (stable sort)
 * 
 * @param {SubscriptionLicense[]} applicableLicenses
 * @returns {SubscriptionLicense|null} Best license or null
 */
export function selectBestLicense(applicableLicenses) {
  if (!applicableLicenses || applicableLicenses.length === 0) {
    return null;
  }
  
  if (applicableLicenses.length === 1) {
    return applicableLicenses[0];
  }
  
  // Sort by precedence rules
  const sorted = [...applicableLicenses].sort((a, b) => {
    // 1. Latest expiration date first
    const expA = new Date(a.subscriptionPlan.expirationDate);
    const expB = new Date(b.subscriptionPlan.expirationDate);
    if (expA.getTime() !== expB.getTime()) {
      return expB - expA; // Descending
    }
    
    // 2. Most recent activation date
    const actA = new Date(a.activationDate);
    const actB = new Date(b.activationDate);
    if (actA.getTime()
