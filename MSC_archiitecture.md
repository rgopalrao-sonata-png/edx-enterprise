# RFC: Multiplex Subscription Licenses (One Learner, Multiple Active Licenses per Enterprise)

## Document Control
- **Author role:** Architecture / cross-repo design
- **Date:** 2026-03-26
- **Status:** Draft for implementation planning
- **Primary business driver:** Unblock Knotion Learning Pathways by enabling multi-license entitlements within one enterprise

---

## 1) Executive Summary

Today, the platform fetches multiple licenses from backend systems but then collapses them into a **single selected license** for most downstream behavior. That MVP simplification blocks customers who need concurrent, program-specific entitlements (multiple CLOSED catalogs and license pools) for the same learner.

This RFC proposes an implementation-ready approach to:
1. Make license collections the source of truth.
2. Preserve backwards compatibility during rollout.
3. Add deterministic per-course license selection.
4. Keep activation, redemption, support views, and learner UX consistent.
5. Ship safely with feature flags and phased migration.

---

## 2) Scope

### In Scope
- BFF responses and internal model changes so learner subsidy data is collection-first.
- Frontend changes to consume/compute from multiple active licenses.
- Correct activation handling when learner has multiple assigned licenses.
- Support/admin read-path consistency for all assigned/activated/revoked licenses.
- Test-first implementation and phased rollout.

### Out of Scope (for this phase)
- Full learner-credit parity redesign.
- Multi-enterprise identity/entitlement merge.
- Full cross-system redemption rewrite in one release.
- Security/performance architecture overhauls unrelated to this feature.
- Analytics/webhooks/bulk management/time-window enforcement enhancements.

---

## 3) Repositories and Responsibilities

## Core repositories
- **enterprise-access**
  - Learner Portal BFF endpoints and response shaping.
  - License retrieval/activation/auto-apply orchestration.
  - Primary API contract boundary to learner portal MFE.
- **frontend-app-learner-portal-enterprise**
  - Learner subsidy selection logic and course applicability.
  - UI/route behavior depending on one vs many license entitlements.
- **license-manager**
  - Source of license records, statuses, activation, admin lookup.
  - Already supports multiple licenses; ensure behavior parity for multi-license consumer flows.

## Additional touchpoint
- **edx-platform** (enterprise support helpers)
  - Existing helper assumes one active enterprise customer user in some paths.
  - Validate compatibility where support tools or contexts infer “single active” records.

---

## 4) Current Implementation (AS-IS)

## 4.1 Enterprise Access (BFF)
Observed behavior:
- Fetches list of learner licenses from license-manager.
- Groups by status.
- Selects one canonical `subscription_license` using st atus priority.
- Exposes both list and singular fields in response, but singular is heavily used downstream.

Key code paths:
- `enterprise_access/apps/api/v1/views/bffs/learner_portal.py`
- `enterprise_access/apps/bffs/handlers.py`
  - `_extract_subscription_license(...)`
  - `transform_subscriptions_result(...)`
  - `check_and_activate_assigned_license(...)`
  - `enroll_in_redeemable_default_enterprise_enrollment_intentions(...)`
- `enterprise_access/apps/bffs/serializers.py`
  - `SubscriptionsSerializer` includes both:
    - `subscription_licenses` (list)
    - `subscription_license` (single)
    - `subscription_plan` (single)

## 4.2 Learner Portal MFE
Observed behavior:
- `useSubscriptions` returns transformed BFF subsidy data.
- Course applicability and subsidy selection often use a singular `subscriptionLicense`.
- Utility functions assume single license applicability against one catalog in key flows.

Key code paths:
- `src/components/app/data/hooks/useSubscriptions.ts`
- `src/components/app/data/services/subsidies/subscriptions.js`
  - `transformSubscriptionsData(...)` picks first applicable/sorted license
- `src/components/app/data/utils.js`
  - `determineSubscriptionLicenseApplicable(subscriptionLicense, catalogsWithCourse)`
- `src/components/course/data/hooks/useUserSubsidyApplicableToCourse.js`

## 4.3 License Manager
Observed behavior:
- Learner list endpoint returns multiple licenses.
- Activation endpoint operates per activation key.
- Admin lookup endpoint already returns all learner licenses for enterprise/user_email.

Key code paths:
- `license_manager/apps/api/v1/views.py`
  - `LearnerLicensesViewSet`
  - `LicenseActivationView`
  - `AdminLicenseLookupViewSet`
- `enterprise_access/apps/api_client/license_manager_client.py`
  - `get_subscription_licenses_for_learner(...)`
  - `activate_license(...)`
  - `get_learner_subscription_licenses_for_admin(...)`

---

## 5) AS-IS Architecture and Detailed Flowcharts

### 5.1 High-Level Current Architecture
```mermaid
flowchart TB
    subgraph "Learner Portal MFE"
        LP1[Route: /:slug/search<br/>/:slug/dashboard]
        LP2[useSubscriptions hook]
        LP3[transformSubscriptionsData]
        LP4[useUserSubsidyApplicableToCourse]
        LP5[determineSubscriptionLicenseApplicable<br/>Single license check]
    end
    
    subgraph "Enterprise Access BFF"
        EA1[LearnerPortalBFFViewSet<br/>dashboard/search/academy]
        EA2[DashboardHandler.load_and_process]
        EA3[load_subscription_licenses]
        EA4[transform_subscriptions_result]
        EA5[_extract_subscription_license<br/>⚠️ BOTTLENECK: Selects ONE]
        EA6[check_and_activate_assigned_license]
        EA7[enroll_in_redeemable_default...intentions<br/>Uses current_activated_license ⚠️]
    end
    
    subgraph "License Manager"
        LM1[LearnerLicensesViewSet<br/>GET /learner-licenses/]
        LM2[License.for_user_and_customer<br/>Returns ALL licenses]
        LM3[LicenseActivationView<br/>POST /license-activation/]
        LM4[AdminLicenseLookupViewSet<br/>GET /admin-license-view/]
    end
    
    subgraph "edx-platform Support"
        EP1[get_active_enterprise_customer_user<br/>⚠️ Assumes single active]
        EP2[Support Tool Learner Profile]
    end

    LP1 --> LP2
    LP2 --> EA1
    EA1 --> EA2
    EA2 --> EA3
    EA3 --> |HTTP GET| LM1
    LM1 --> LM2
    LM2 --> |Returns List| EA3
    EA3 --> EA4
    EA4 --> EA5
    EA5 --> |Singular license selected| EA6
    EA6 --> |POST activation| LM3
    EA2 --> EA7
    EA7 --> |Uses ONE license only| EA2
    EA2 --> |Response with singular + list| LP2
    LP2 --> LP3
    LP3 --> |Extracts FIRST license| LP4
    LP4 --> LP5
    LP5 --> |Checks ONE catalog| LP4
    
    EP2 --> |Query| LM4
    LM4 --> |Returns multiple| EP2
```

### 5.2 Detailed AS-IS Flow (Request to Response)

```mermaid
sequenceDiagram
    participant LP as Learner Portal<br/>(MFE)
    participant BFF as Enterprise Access BFF<br/>(handlers.py)
    participant LMC as LicenseManagerUserApiClient<br/>(license_manager_client.py)
    participant LM as License Manager API<br/>(views.py)
    participant DB as License DB

    Note over LP: User navigates to<br/>/:enterpriseSlug/dashboard
    
    LP->>BFF: POST /api/v1/bffs/learner/dashboard/
    Note over BFF: DashboardHandler.load_and_process()
    
    BFF->>BFF: load_subscription_licenses()
    BFF->>LMC: get_subscription_licenses_for_learner<br/>(enterprise_uuid)
    
    LMC->>LM: GET /learner-licenses/?enterprise_customer_uuid=X<br/>&include_revoked=true&current_plans_only=false
    
    LM->>DB: License.for_user_and_customer<br/>(user_email, enterprise_uuid)
    DB-->>LM: Returns [License1, License2, License3]
    LM-->>LMC: {results: [License1, License2, License3],<br/>customer_agreement: {...}}
    
    LMC-->>BFF: subscriptions_result with all licenses
    
    Note over BFF: ⚠️ BOTTLENECK STARTS HERE
    BFF->>BFF: transform_subscriptions_result()
    BFF->>BFF: Group licenses by status<br/>{activated: [L1, L2], assigned: [L3]}
    
    BFF->>BFF: _extract_subscription_license()<br/>Priority: ACTIVATED > ASSIGNED > REVOKED
    Note over BFF: ⚠️ Selects ONLY License1<br/>Discards L2, L3 for downstream
    
    BFF->>BFF: process_subscription_licenses()
    alt Has assigned licenses
        BFF->>BFF: check_and_activate_assigned_license()
        loop For each assigned license
            BFF->>LM: POST /license-activation/?activation_key=X
            LM-->>BFF: Activated license
        end
        BFF->>BFF: Re-extract single license after activation
    end
    
    BFF->>BFF: enroll_in_redeemable_default...<br/>Uses self.current_activated_license ⚠️
    Note over BFF: Only ONE license used for<br/>default enrollment mapping
    
    BFF-->>LP: Response:<br/>{subscription_licenses: [L1,L2,L3],<br/>subscription_license: L1 ⚠️,<br/>subscription_plan: L1.plan}
    
    Note over LP: MFE Hook Processing
    LP->>LP: useSubscriptions() transforms data
    LP->>LP: transformSubscriptionsData()<br/>Extracts first from Object.values(...).flat()[0]
    
    Note over LP: ⚠️ MFE also selects ONE license
    LP->>LP: useUserSubsidyApplicableToCourse()
    LP->>LP: determineSubscriptionLicenseApplicable<br/>(subscriptionLicense, catalogs)
    Note over LP: Checks ONLY ONE license<br/>against catalog membership
    
    LP->>LP: Render course with single<br/>license entitlement
```

### 5.3 Current Bottleneck Analysis (Code-Level)

#### **Bottleneck 1: BFF License Selection**
**Location:** `enterprise-access/enterprise_access/apps/bffs/handlers.py`

```python
# Line ~262-280
def _extract_subscription_license(self, subscription_licenses_by_status):
    """
    Extract subscription licenses from the subscription licenses by status.
    """
    license_status_priority_order = [
        LicenseStatuses.ACTIVATED,
        LicenseStatuses.ASSIGNED,
        LicenseStatuses.REVOKED,
    ]
    subscription_license = next(
        (
            license
            for status in license_status_priority_order
            for license in subscription_licenses_by_status.get(status, [])
        ),
        None,   # ⚠️ Returns ONLY FIRST match across all statuses
    )
    return subscription_license
```

**Impact:** Even with 3 activated licenses from different catalogs, only the first one is exposed as canonical.

#### **Bottleneck 2: Default Enrollment with Single License**
**Location:** `enterprise-access/enterprise_access/apps/bffs/handlers.py`

```python
# Line ~579-644
def enroll_in_redeemable_default_enterprise_enrollment_intentions(self):
    # ...
    if not self.current_activated_license:  # ⚠️ Uses property that returns ONE
        logger.info("No activated license found...")
        return

    license_uuids_by_course_run_key = {}
    for enrollment_intention in needs_enrollment_enrollable:
        subscription_plan = self.current_activated_license.get('subscription_plan', {})
        subscription_catalog = subscription_plan.get('enterprise_catalog_uuid')
        # ⚠️ Maps ALL courses to SAME license, ignoring other active licenses
```

**Impact:** Courses from catalog B won't auto-enroll if license A was selected first.

#### **Bottleneck 3: MFE License Selection**
**Location:** `frontend-app-learner-portal-enterprise/src/components/app/data/services/subsidies/subscriptions.js`

```javascript
// Line ~219-238
export function transformSubscriptionsData({ customerAgreement, subscriptionLicenses }) {
  // ...groups licenses by status...
  
  // ⚠️ Extracts FIRST license from flattened status groups
  const applicableSubscriptionLicense = Object.values(
    subscriptionsData.subscriptionLicensesByStatus
  ).flat()[0];
  
  if (applicableSubscriptionLicense) {
    subscriptionsData.subscriptionLicense = applicableSubscriptionLicense;
    subscriptionsData.subscriptionPlan = applicableSubscriptionLicense.subscriptionPlan;
  }
  // ⚠️ Result: only ONE license available to downstream hooks
```

#### **Bottleneck 4: Course Applicability Single-License Check**
**Location:** `frontend-app-learner-portal-enterprise/src/components/app/data/utils.js`

```javascript
// Line ~1076-1081
export function determineSubscriptionLicenseApplicable(subscriptionLicense, catalogsWithCourse) {
  return (
    subscriptionLicense?.status === LICENSE_STATUS.ACTIVATED
    && subscriptionLicense?.subscriptionPlan.isCurrent
    && catalogsWithCourse.includes(subscriptionLicense?.subscriptionPlan.enterpriseCatalogUuid)
  );
  // ⚠️ Checks ONLY ONE license; if it doesn't match catalog, returns false
  //    even if another activated license DOES match
}
```

### 5.4 Data Flow Map (Current State)

```
┌─────────────────────────────────────────────────────────────────────┐
│ License Manager Database                                             │
│                                                                      │
│  Learner: alice@company.com                                         │
│  Enterprise: acme-corp (uuid: 1234...)                              │
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │ License A       │  │ License B       │  │ License C       │    │
│  │ Status: ACTIVE  │  │ Status: ACTIVE  │  │ Status: ASSIGNED│    │
│  │ Catalog: cat-A  │  │ Catalog: cat-B  │  │ Catalog: cat-C  │    │
│  │ Plan: Current   │  │ Plan: Current   │  │ Plan: Current   │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────┐
        │ License Manager API Response                 │
        │ GET /learner-licenses/                       │
        │                                              │
        │ {                                            │
        │   "results": [                               │
        │     {"uuid": "A", "status": "activated",...},│
        │     {"uuid": "B", "status": "activated",...},│
        │     {"uuid": "C", "status": "assigned",...}  │
        │   ],                                         │
        │   "customer_agreement": {...}                │
        │ }                                            │
        └──────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────┐
        │ Enterprise Access BFF Processing             │
        │ handlers.py: _extract_subscription_license() │
        │                                              │
        │ ⚠️ Selection Logic:                          │
        │ Priority order: ACTIVATED > ASSIGNED         │
        │ Within ACTIVATED: First in list (License A)  │
        │                                              │
        │ SELECTED: License A                          │
        │ DISCARDED: License B, License C              │
        └──────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────┐
        │ BFF Response to MFE                          │
        │                                              │
        │ {                                            │
        │   "subscription_licenses": [A, B, C],  ✓    │
        │   "subscription_license": A,           ⚠️    │
        │   "subscription_plan": A.plan          ⚠️    │
        │ }                                            │
        └──────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────┐
        │ MFE transformSubscriptionsData()             │
        │                                              │
        │ const applicableSubscriptionLicense =        │
        │   Object.values(byStatus).flat()[0]         │
        │                                              │
        │ SELECTED: License A (again)                  │
        │ AVAILABLE TO HOOKS: Only License A           │
        └──────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────┐
        │ Course Page: course-in-catalog-B             │
        │                                              │
        │ determineSubscriptionLicenseApplicable()     │
        │   checks: License A catalog === catalog-B?   │
        │   Result: FALSE ❌                            │
        │                                              │
        │ User sees: "Not eligible for this course"    │
        │ Reality: License B WOULD grant access! ❌     │
        └──────────────────────────────────────────────┘
```

---

## 6) Target Architecture (TO-BE)

### Design principles
1. **Collection-first contract:** `subscription_licenses` is canonical.
2. **Deterministic selection by course:** choose per-course applicable license, not global singleton.
3. **Backward compatibility:** preserve legacy singular fields temporarily.
4. **Non-breaking rollout:** feature flags at BFF + MFE.
5. **Parity and traceability:** activation/support status must match learner-visible state.

### Behavioral target
- A learner may hold multiple active licenses in same enterprise simultaneously.
- For each course page/action, system evaluates all active/current licenses and catalogs.
- If multiple licenses apply, deterministic tie-breaker chooses one.
- Support/admin views show complete license set and statuses.

---

## 7) TO-BE Architecture and Detailed Implementation

### 7.1 High-Level Target Architecture
```mermaid
flowchart TB
    subgraph "Learner Portal MFE (Enhanced)"
        LP1[Route: /:slug/course/:key]
        LP2[useSubscriptions hook<br/>✓ Returns collection]
        LP3[transformSubscriptionsData<br/>✓ Preserves all licenses]
        LP4[useUserSubsidyApplicableToCourse<br/>✓ Enhanced multi-license logic]
        LP5[NEW: getApplicableLicensesForCourse<br/>Returns matching licenses array]
        LP6[NEW: selectBestLicense<br/>Deterministic tie-breaker]
    end
    
    subgraph "Enterprise Access BFF (Refactored)"
        EA1[LearnerPortalBFFViewSet<br/>Enhanced response]
        EA2[DashboardHandler.load_and_process<br/>✓ Multi-license aware]
        EA3[load_subscription_licenses]
        EA4[transform_subscriptions_result<br/>✓ Collection-first processing]
        EA5[NEW: applicable_licenses_by_catalog<br/>Optional computed field]
        EA6[check_and_activate_assigned_license<br/>✓ Handles multiple activations]
        EA7[NEW: enroll_in_redeemable_with_best_match<br/>Per-course license mapping]
    end
    
    subgraph "License Manager (No Changes)"
        LM1[LearnerLicensesViewSet<br/>Returns ALL licenses]
        LM2[LicenseActivationView<br/>Per-license activation]
        LM3[AdminLicenseLookupViewSet<br/>Complete license list]
    end
    
    subgraph "Feature Flags"
        FF1[ENABLE_MULTI_LICENSE_ENTITLEMENTS_BFF]
        FF2[ENABLE_MULTI_LICENSE_ENTITLEMENTS_MFE]
    end

    LP1 --> LP2
    LP2 --> EA1
    FF1 -.->|Controls| EA2
    EA1 --> EA2
    EA2 --> EA3
    EA3 --> |HTTP GET| LM1
    LM1 --> |Returns ALL| EA3
    EA3 --> EA4
    EA4 --> EA5
    EA5 --> |Preserves collection| EA6
    EA6 --> |Multiple POST calls| LM2
    EA2 --> EA7
    EA7 --> |Maps each course to best license| EA2
    EA2 --> |Enhanced response| LP2
    
    LP2 --> LP3
    LP3 --> |All licenses available| LP4
    FF2 -.->|Controls| LP4
    LP4 --> LP5
    LP5 --> |Filters by catalog| LP6
    LP6 --> |Selected for THIS course| LP4
```

### 7.2 Detailed TO-BE Flow (Request to Response)

```mermaid
sequenceDiagram
    participant LP as Learner Portal<br/>(MFE)
    participant BFF as Enterprise Access BFF<br/>(handlers.py - Enhanced)
    participant LMC as LicenseManagerUserApiClient
    participant LM as License Manager API
    participant DB as License DB

    Note over LP: User navigates to<br/>/:enterpriseSlug/course/courseX
    
    LP->>BFF: POST /api/v1/bffs/learner/dashboard/
    Note over BFF: Flag: ENABLE_MULTI_LICENSE_ENTITLEMENTS_BFF=True
    
    BFF->>BFF: DashboardHandler.load_and_process()
    BFF->>BFF: load_subscription_licenses()
    BFF->>LMC: get_subscription_licenses_for_learner(uuid)
    
    LMC->>LM: GET /learner-licenses/?enterprise_customer_uuid=X
    LM->>DB: License.for_user_and_customer()
    DB-->>LM: [License A (cat-A), License B (cat-B), License C (cat-C)]
    LM-->>BFF: {results: [A, B, C], customer_agreement: {...}}
    
    Note over BFF: ✓ NEW: Collection-First Processing
    BFF->>BFF: transform_subscriptions_result()
    BFF->>BFF: Group by status<br/>{activated: [A, B], assigned: [C]}
    
    alt Feature Flag OFF
        BFF->>BFF: _extract_subscription_license()<br/>Legacy: Select first
    else Feature Flag ON
        BFF->>BFF: ✓ Preserve all licenses<br/>No singular extraction
        BFF->>BFF: ✓ NEW: compute_applicable_licenses_by_catalog()
        Note over BFF: Optional: Pre-compute catalog mappings<br/>{cat-A: [A], cat-B: [B], cat-C: [C]}
    end
    
    BFF->>BFF: process_subscription_licenses()
    alt Has multiple assigned licenses
        BFF->>BFF: check_and_activate_assigned_license()
        loop For EACH assigned license
            BFF->>LM: POST /license-activation/?activation_key=C
            LM-->>BFF: ✓ Activated license C
        end
        BFF->>BFF: ✓ Update ALL activated in response
    end
    
    BFF->>BFF: ✓ NEW: enroll_in_redeemable_with_best_match()
    Note over BFF: For each enrollment intention,<br/>find best matching active license
    loop For each enrollable course
        BFF->>BFF: Find licenses where<br/>catalog contains course
        BFF->>BFF: Select best match (latest expiration)
        Note over BFF: License A for course-in-cat-A<br/>License B for course-in-cat-B
    end
    
    BFF-->>LP: Enhanced Response:<br/>{subscription_licenses: [A,B,C],<br/>applicable_licenses_by_catalog: {...},<br/>subscription_license: A ⚠️ Deprecated,<br/>selection_policy_version: "v2"}
    
    Note over LP: ✓ MFE Enhanced Processing
    LP->>LP: useSubscriptions() - enhanced
    LP->>LP: transformSubscriptionsData()<br/>✓ Preserves ALL licenses in state
    
    Note over LP: Course Page Rendering
    LP->>LP: useUserSubsidyApplicableToCourse(courseX)
    alt Feature Flag OFF
        LP->>LP: Legacy: Check single subscriptionLicense
    else Feature Flag ON
        LP->>LP: ✓ NEW: getApplicableLicensesForCourse(courseX)
        Note over LP: Filters all licenses by:<br/>- status=activated<br/>- plan.isCurrent=true<br/>- catalog contains courseX
        LP->>LP: Returns [License B] (matches cat-B)
        LP->>LP: ✓ selectBestLicense([License B])
        Note over LP: If multiple: latest expiration wins
    end
    
    LP->>LP: ✓ Render enrollment with correct<br/>license B entitlement
```

### 7.3 New Implementation Details (Code-Level)

#### **Enhancement 1: BFF Collection Preservation**
**Location:** `enterprise-access/enterprise_access/apps/bffs/handlers.py`

```python
# NEW: Around line ~280+
def transform_subscriptions_result(self, subscriptions_result):
    """Enhanced to preserve collection-first semantics"""
    subscription_licenses = subscriptions_result.get('results', [])
    subscription_licenses_by_status = {}
    
    # Sort by current plans first
    ordered_subscription_licenses = sorted(
        subscription_licenses,
        key=lambda license: not license.get('subscription_plan', {}).get('is_current'),
    )
    
    for subscription_license in ordered_subscription_licenses:
        status = subscription_license.get('status')
        if status not in subscription_licenses_by_status:
            subscription_licenses_by_status[status] = []
        subscription_licenses_by_status[status].append(subscription_license)
    
    customer_agreement = subscriptions_result.get('customer_agreement')
    
    # ✓ NEW: Optional catalog-based grouping
    if getattr(settings, 'ENABLE_MULTI_LICENSE_ENTITLEMENTS_BFF', False):
        applicable_licenses_by_catalog = self._compute_catalog_mapping(
            subscription_licenses_by_status
        )
    else:
        applicable_licenses_by_catalog = None
    
    # DEPRECATED: For compatibility only
    subscription_license = self._extract_subscription_license(
        subscription_licenses_by_status
    )
    subscription_plan = subscription_license.get('subscription_plan') if subscription_license else None
    
    return {
        'customer_agreement': customer_agreement,
        'subscription_licenses': subscription_licenses,  # ✓ Complete list
        'subscription_licenses_by_status': subscription_licenses_by_status,
        'applicable_licenses_by_catalog': applicable_licenses_by_catalog,  # ✓ NEW
        'subscription_license': subscription_license,  # ⚠️ Deprecated
        'subscription_plan': subscription_plan,  # ⚠️ Deprecated
        'selection_policy_version': 'v2' if applicable_licenses_by_catalog else 'v1',
        # ... other fields
    }

def _compute_catalog_mapping(self, subscription_licenses_by_status):
    """NEW: Pre-compute catalog to licenses mapping"""
    activated_licenses = subscription_licenses_by_status.get(
        LicenseStatuses.ACTIVATED, []
    )
    current_activated = [
        lic for lic in activated_licenses
        if lic.get('subscription_plan', {}).get('is_current')
    ]
    
    catalog_map = {}
    for license in current_activated:
        catalog_uuid = license.get('subscription_plan', {}).get('enterprise_catalog_uuid')
        if catalog_uuid:
            if catalog_uuid not in catalog_map:
                catalog_map[catalog_uuid] = []
            catalog_map[catalog_uuid].append(license)
    
    return catalog_map
```

#### **Enhancement 2: Multi-License Enrollment Mapping**
**Location:** `enterprise-access/enterprise_access/apps/bffs/handlers.py`

```python
# NEW: Enhanced enrollment intention handling
def enroll_in_redeemable_default_enterprise_enrollment_intentions(self):
    """Enhanced to map courses to best-matching licenses"""
    enrollment_statuses = self.default_enterprise_enrollment_intentions.get(
        'enrollment_statuses', {}
    )
    needs_enrollment = enrollment_statuses.get('needs_enrollment', {})
    needs_enrollment_enrollable = needs_enrollment.get('enrollable', [])
    
    if not needs_enrollment_enrollable:
        return
    
    # ✓ NEW: Get ALL activated licenses, not just one
    activated_licenses = self._current_subscription_licenses_for_status(
        LicenseStatuses.ACTIVATED
    )
    
    if not activated_licenses:
        logger.info("No activated licenses found")
        return
    
    # ✓ NEW: Map each course to best matching license
    license_uuids_by_course_run_key = {}
    
    for enrollment_intention in needs_enrollment_enrollable:
        course_run_key = enrollment_intention['course_run_key']
        applicable_catalog_uuids = enrollment_intention.get(
            'applicable_enterprise_catalog_uuids', []
        )
        
        # Find licenses whose catalog matches this course
        matching_licenses = [
            lic for lic in activated_licenses
            if lic.get('subscription_plan', {}).get('enterprise_catalog_uuid')
            in applicable_catalog_uuids
        ]
        
        if matching_licenses:
            # Deterministic selection: latest expiration
            best_license = max(
                matching_licenses,
                key=lambda l: l.get('subscription_plan', {}).get('expiration_date', '')
            )
            license_uuids_by_course_run_key[course_run_key] = best_license['uuid']
    
    if license_uuids_by_course_run_key:
        response_payload = self._request_default_enrollment_realizations(
            license_uuids_by_course_run_key
        )
        # ... handle response
```

#### **Enhancement 3: MFE Multi-License Course Applicability**
**Location:** `frontend-app-learner-portal-enterprise/src/components/app/data/utils.js`

```javascript
// NEW: Multi-license version
export function getApplicableLicensesForCourse(subscriptionLicenses, catalogsWithCourse) {
  if (!subscriptionLicenses || !Array.isArray(subscriptionLicenses)) {
    return [];
  }
  
  return subscriptionLicenses.filter(license => (
    license?.status === LICENSE_STATUS.ACTIVATED
    && license?.subscriptionPlan?.isCurrent
    && catalogsWithCourse.includes(license?.subscriptionPlan?.enterpriseCatalogUuid)
  ));
}

export function selectBestLicense(applicableLicenses) {
  if (!applicableLicenses || applicableLicenses.length === 0) {
    return null;
  }
  
  if (applicableLicenses.length === 1) {
    return applicableLicenses[0];
  }
  
  // Deterministic tie-breaker: latest expiration, then activation date, then UUID
  return applicableLicenses.sort((a, b) => {
    const expA = new Date(a.subscriptionPlan.expirationDate);
    const expB = new Date(b.subscriptionPlan.expirationDate);
    if (expA !== expB) {
      return expB - expA; // Latest expiration first
    }
    
    const actA = new Date(a.activationDate);
    const actB = new Date(b.activationDate);
    if (actA !== actB) {
      return actB - actA;
    }
    
    // Final fallback: UUID lexical
    return b.uuid.localeCompare(a.uuid);
  })[0];
}
```

#### **Enhancement 4: Enhanced useUserSubsidyApplicableToCourse**
**Location:** `frontend-app-learner-portal-enterprise/src/components/course/data/hooks/useUserSubsidyApplicableToCourse.js`

```javascript
const useUserSubsidyApplicableToCourse = () => {
  const { courseKey } = useParams();
  const {
    data: {
      subscriptionLicenses,  // ✓ Full collection
      subscriptionLicense,   // ⚠️ Deprecated fallback
    },
  } = useSubscriptions();
  
  const {
    data: {
      catalogList: catalogsWithCourse,
    },
  } = useEnterpriseCustomerContainsContentSuspense([courseKey]);
  
  // ✓ NEW: Feature flag check
  const multiLicenseEnabled = features.ENABLE_MULTI_LICENSE_ENTITLEMENTS;
  
  let applicableSubscriptionLicense;
  
  if (multiLicenseEnabled && subscriptionLicenses) {
    // ✓ NEW: Multi-license path
    const applicableLicenses = getApplicableLicensesForCourse(
      subscriptionLicenses,
      catalogsWithCourse
    );
    applicableSubscriptionLicense = selectBestLicense(applicableLicenses);
  } else {
    // Legacy: single license check
    const isApplicable = determineSubscriptionLicenseApplicable(
      subscriptionLicense,
      catalogsWithCourse
    );
    applicableSubscriptionLicense = isApplicable ? subscriptionLicense : null;
  }
  
  const userSubsidyApplicableToCourse = getSubsidyToApplyForCourse({
    applicableSubscriptionLicense,
    // ... other subsidies
  });
  
  return { userSubsidyApplicableToCourse, ... };
};
```

### 7.4 Target Data Flow (TO-BE State)

```
┌─────────────────────────────────────────────────────────────────────┐
│ License Manager Database (Unchanged)                                 │
│                                                                      │
│  Learner: alice@company.com                                         │
│  Enterprise: acme-corp                                              │
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │ License A       │  │ License B       │  │ License C       │    │
│  │ Status: ACTIVE  │  │ Status: ACTIVE  │  │ Status: ASSIGNED│    │
│  │ Catalog: cat-A  │  │ Catalog: cat-B  │  │ Catalog: cat-C  │    │
│  │ Plan: Current   │  │ Plan: Current   │  │ Plan: Current   │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────┐
        │ License Manager API Response (Unchanged)      │
        │                                              │
        │ {                                            │
        │   "results": [A, B, C],                      │
        │   "customer_agreement": {...}                │
        │ }                                            │
        └──────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────┐
        │ ✓ Enterprise Access BFF (Enhanced)           │
        │ Flag: ENABLE_MULTI_LICENSE_ENTITLEMENTS=True │
        │                                              │
        │ ✓ Collection-First Processing:               │
        │ - Preserve ALL licenses                      │
        │ - Compute catalog mappings                   │
        │ - Deprecated singular fields for compat      │
        │                                              │
        │ AVAILABLE: Licenses A, B, C                  │
        │ CATALOG MAP: {cat-A:[A], cat-B:[B], cat-C:[C]}│
        └──────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────┐
        │ ✓ Enhanced BFF Response                      │
        │                                              │
        │ {                                            │
        │   "subscription_licenses": [A,B,C],     ✓✓  │
        │   "subscription_licenses_by_status": {       │
        │     "activated": [A, B],                     │
        │     "assigned": [C]                          │
        │   },                                         │
        │   "applicable_licenses_by_catalog": {   ✓NEW │
        │     "cat-A": [A],                            │
        │     "cat-B": [B],                            │
        │     "cat-C": [C]                             │
        │   },                                         │
        │   "subscription_license": A,     ⚠️ Deprecated│
        │   "selection_policy_version": "v2"      ✓NEW │
        │ }                                            │
        └──────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────┐
        │ ✓ MFE Enhanced Processing                    │
        │ Flag: ENABLE_MULTI_LICENSE_ENTITLEMENTS=True │
        │                                              │
        │ transformSubscriptionsData():                │
        │ - Preserves ALL licenses in state            │
        │ - No singleton extraction                    │
        │                                              │
        │ AVAILABLE: Licenses A, B, C                  │
        └──────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────┐
        │ ✓ Course Page: course-in-catalog-B           │
        │                                              │
        │ getApplicableLicensesForCourse():            │
        │   Input: [A, B, C], catalogs: [cat-B]        │
        │   Filters: activated + current + catalog     │
        │   Result: [B] ✓✓                             │
        │                                              │
        │ selectBestLicense([B]):                      │
        │   Result: License B ✓✓                       │
        │                                              │
        │ User sees: "Enroll with License B" ✓✓✓       │
        │ Reality: License B grants access! ✓✓✓        │
        └──────────────────────────────────────────────┘
```

---

## 8) API Schema Delta Plan

## 8.1 BFF response (enterprise-access)
### Current fields
- `subscriptions.subscription_licenses` (list)
- `subscriptions.subscription_licenses_by_status` (grouped list)
- `subscriptions.subscription_license` (single)
- `subscriptions.subscription_plan` (single)

### Proposed contract
1. Keep existing list fields unchanged (canonical source).
2. Introduce optional computed fields for migration clarity:
   - `subscriptions.applicable_subscription_licenses` (list; optional)
   - `subscriptions.selection_policy_version` (string; optional)
3. Keep `subscription_license` and `subscription_plan` as **deprecated compatibility fields**.
4. Add deprecation metadata in API docs/changelog with removal timeline.

### Compatibility strategy
- **Phase 1/2:** populate both new and old fields.
- **Phase 3:** old fields behind fallback flag only.
- **Phase 4:** remove old fields after adoption and telemetry thresholds.

## 8.2 Internal type changes (MFE)
- Update TS types and selectors to model:
  - `subscriptionLicenses: SubscriptionLicense[]`
  - `applicableSubscriptionLicenses?: SubscriptionLicense[]`
- Keep temporary `subscriptionLicense?: SubscriptionLicense | null` for compatibility.

## 8.3 License-manager API
- No mandatory schema changes required for MVP.
- Optional hardening:
  - document ordering guarantees (if any)
  - explicit pagination behavior notes for large license sets

---

## 9) Selection Policy (Deterministic)

## Inputs
- Course catalog membership (`catalogsWithCourse`).
- License attributes: `status`, `subscription_plan.is_current`, `subscription_plan.enterprise_catalog_uuid`, dates.

## Candidate filter
1. `status == activated`
2. `subscription_plan.is_current == true`
3. `subscription_plan.enterprise_catalog_uuid in catalogsWithCourse`

## Tie-breaker (recommended)
Order by:
1. latest `subscription_plan.expiration_date`
2. latest `activation_date`
3. stable UUID lexical fallback

This guarantees deterministic behavior without requiring backend persistence changes.

---

## 10) Migration and Rollout Plan

## Phase 0: Discovery + Test Baseline
- Inventory all single-license assumptions in BFF and MFE.
- Add contract tests proving multi-license payloads are preserved.
- Establish local reproducible fixtures:
  - one learner, one enterprise, multiple active/assigned licenses, different CLOSED catalogs.

## Phase 1: Backend Collection-First Read Path
- Refactor BFF handlers to avoid using a global singular license for new logic.
- Keep existing singular fields populated for compatibility.
- Ensure activation loop handles multiple assigned licenses robustly.

## Phase 2: MFE Dual-Read with Feature Flag
- Add `ENABLE_MULTI_LICENSE_ENTITLEMENTS` flag in MFE.
- Under flag: compute course applicability from license collections.
- Without flag: preserve legacy single-license behavior.

## Phase 3: Support/Admin Consistency Validation
- Validate admin learner profile and support tool output across all assigned licenses.
- Reconcile any mismatch between learner-visible and admin-visible activation status.

## Phase 4: Cutover + Deprecation
- Turn on flags for pilot enterprise(s).
- Observe errors/metrics.
- Expand rollout.
- Remove legacy singular dependency after SLO period and no regressions.

---

## 11) Feature Flags

## Backend
- `ENABLE_MULTI_LICENSE_ENTITLEMENTS_BFF` (bool)
  - Enables new collection-first processing and course-level selection helpers.

## Frontend
- `ENABLE_MULTI_LICENSE_ENTITLEMENTS` (bool)
  - Enables multi-license subsidy applicability logic.

## Flag behavior matrix
- both off: legacy behavior
- backend on + frontend off: safe compatibility mode
- backend off + frontend on: unsupported (prevent via config guard)
- both on: target behavior

---

## 12) Implementation Checklist by Repository

## A) enterprise-access
### API/BFF
- [ ] Refactor `transform_subscriptions_result` to avoid relying on singleton for new code paths.
- [ ] Introduce optional `applicable_subscription_licenses` and `selection_policy_version` in serializer.
- [ ] Keep singular fields for compatibility with clear deprecation comments/docs.

### Activation
- [ ] Confirm activation loop updates grouped data and list data without singleton side-effects.
- [ ] Add idempotence coverage for repeated activation attempts.

### Enrollment intention realization
- [ ] Replace single `current_activated_license` usage with course-level license selection helper.

### Docs
- [ ] Update API docs + changelog with deprecation timeline.

## B) frontend-app-learner-portal-enterprise
### Data model and hooks
- [ ] Extend subscription transformed data model for collection-first usage.
- [ ] Keep temporary compatibility accessor `subscriptionLicense`.

### Course logic
- [ ] Add helper `determineApplicableSubscriptionLicenses(...)` (list result).
- [ ] Update `useUserSubsidyApplicableToCourse` to use per-course selected license from list.
- [ ] Ensure subsidy precedence logic still works (license > coupon/credit/offer as currently intended).

### UI/UX
- [ ] Decide if learner-facing license switcher is required in MVP.
- [ ] If not, use deterministic auto-selection and expose in telemetry.

## C) license-manager
### API behavior validation
- [ ] Confirm learner-licenses and admin-license-view return complete sets with expected filters.
- [ ] Validate activation endpoint behavior with multiple assigned licenses for same user.

### Optional hardening
- [ ] Add integration tests for same-user multi-license activation sequences.

## D) edx-platform (support helper touchpoints)
- [ ] Validate `get_active_enterprise_customer_user` assumptions do not break support views for this project scope.
- [ ] If needed, isolate helper usage from subscription-license-specific support paths.

---

## 13) Test Matrix (Exact, Repo-by-Repo)

## 13.1 enterprise-access test matrix

### Unit tests
1. **BFF transforms**
   - Input: 3 licenses (2 activated current, 1 assigned current, different catalogs)
   - Expect: all licenses preserved, grouped correctly, deprecation fields still populated.
2. **Activation flow**
   - Input: 2 assigned current licenses with valid keys
   - Expect: activation called for each; statuses updated in response model.
3. **Default enrollment realization**
   - Input: course set spanning catalog A and B
   - Expect: each course mapped to applicable activated license UUID.

### API tests
4. `learner/dashboard` response contract under flag on/off.
5. `learner/search` and `learner/academy` contract parity.

### Regression tests
6. Single-license learner still behaves exactly as before.

## 13.2 frontend-app-learner-portal-enterprise test matrix

### Unit tests
1. `transformSubscriptionsData` preserves full list and deterministic sort.
2. New helper returns all applicable licenses for course catalogs.
3. Deterministic tie-breaker chooses expected UUID for equal candidates.

### Hook tests
4. `useUserSubsidyApplicableToCourse`
   - case A: one applicable license
   - case B: multiple applicable licenses
   - case C: none applicable, fallback reasons unchanged.

### Integration tests
5. Course page renders enroll CTA with selected license from list.
6. Existing single-license snapshots remain valid with flag off.

## 13.3 license-manager test matrix

### API tests
1. `learner-licenses` returns all licenses for user/customer with filters:
   - `current_plans_only=true/false`
   - `include_revoked=true/false`
2. `license-activation` with multiple assigned licenses for same user:
   - valid key activates correct license only
   - second activation remains idempotent.
3. `admin-license-view` returns complete paginated set for user_email/customer.

## 13.4 Cross-repo E2E scenarios

1. **Multi-license dual catalog success**
   - Learner has active licenses in catalogs A + B.
   - Course in A uses license A; course in B uses license B.
2. **Mixed status**
   - assigned(A), activated(B), revoked(C).
   - A can activate, B usable immediately, C excluded for redemption.
3. **No disruption single-license**
   - Legacy enterprise with one active license unaffected.
4. **Support consistency**
   - Learner-visible status equals admin profile/status output.

---

## 14) Data and Observability

## Metrics (recommended)
- Count of learners with >1 active current license per enterprise.
- Entitlement selection outcome distribution (selected license UUID hash/bucket).
- Activation attempts/success/failure rates by status and enterprise.
- MFE fallback-to-legacy path usage while flags enabled.

## Logging
- Structured logs with:
  - enterprise UUID
  - learner ID
  - candidate license count
  - selected license UUID
  - reason/tie-break attributes

## Alerts
- Spike in activation errors.
- Increased enrollment failures where candidate license count > 1.

---

## 15) Risks and Mitigations

1. **Risk:** Regressions in subsidy precedence logic.
   - **Mitigation:** Freeze precedence order in tests and codify deterministic selection.
2. **Risk:** Hidden singleton assumptions in less-traveled routes.
   - **Mitigation:** grep/audit + contract tests for all BFF learner routes.
3. **Risk:** Cross-repo rollout mismatch.
   - **Mitigation:** enforce flag compatibility matrix and staged rollout.
4. **Risk:** Support tool inconsistency.
   - **Mitigation:** explicit cross-check scenarios in E2E and signoff checklist.

---

## 16) Open Questions (for discovery signoff)

1. Should UI expose a learner-visible “license source/program” indicator per course redemption?
2. Is deterministic auto-selection sufficient for MVP, or do any customers require manual chooser in phase 1?
3. What deprecation window is acceptable for singular fields (`subscription_license`, `subscription_plan`)?
4. Do any downstream consumers outside learner portal still depend on singleton semantics?

---

## 17) Proposed Delivery Sequence (2-Week Sprints Example)

## Sprint 1
- Finalize selection policy and compatibility schema.
- Implement backend dual-contract and tests.
- Add feature flags and telemetry scaffolding.

## Sprint 2
- Implement MFE collection-first logic under flag.
- Complete cross-repo integration testing.
- Pilot rollout for Knotion enterprise.

## Sprint 3 (optional hardening)
- Expand rollout.
- Remove or lock down legacy singleton reads where safe.
- Finalize deprecation announcement and removal timeline.

---

## 18) Ready-to-Run Engineering Ticket Template

### Ticket Title
Enable collection-first multi-license entitlement selection for learner portal

### Acceptance Criteria
- Learner with multiple active licenses can redeem courses in each corresponding catalog.
- BFF returns unchanged list contracts and new optional migration fields.
- Legacy singleton behavior remains available behind compatibility fallback.
- Unit/integration tests pass per repository matrix.
- No regression for single-license users.

### Definition of Done
- Code + tests merged in required repos.
- Flags documented and configured.
- Pilot validation complete.
- Monitoring dashboards and alerts enabled.

---

## 19) Appendix: Quick File Map

- `enterprise-access/enterprise_access/apps/api/v1/views/bffs/learner_portal.py`
- `enterprise-access/enterprise_access/apps/bffs/handlers.py`
- `enterprise-access/enterprise_access/apps/bffs/serializers.py`
- `enterprise-access/enterprise_access/apps/api_client/license_manager_client.py`
- `frontend-app-learner-portal-enterprise/src/components/app/data/hooks/useSubscriptions.ts`
- `frontend-app-learner-portal-enterprise/src/components/app/data/services/subsidies/subscriptions.js`
- `frontend-app-learner-portal-enterprise/src/components/app/data/utils.js`
- `frontend-app-learner-portal-enterprise/src/components/course/data/hooks/useUserSubsidyApplicableToCourse.js`
- `license-manager/license_manager/apps/api/v1/views.py`
- `edx-platform/openedx/features/enterprise_support/api.py`

---

## 20) Final Recommendation
Proceed with **dual-contract, flag-gated, collection-first** implementation. This delivers Knotion’s requirement with minimal blast radius and clear migration guardrails, while keeping current single-license tenants stable during adoption.
