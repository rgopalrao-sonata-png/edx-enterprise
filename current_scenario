# Current License Selection Process - Code Walkthrough

**Date:** March 26, 2026  
**Purpose:** Detailed code-level explanation of how subscription licenses are currently selected in the edX platform  
**Related:** [multiplex-subscription-licenses-rfc.md](multiplex-subscription-licenses-rfc.md)

---

## Table of Contents

1. [Overview](#overview)
2. [Step-by-Step Flow](#step-by-step-flow)
3. [The 4 Bottlenecks](#the-4-bottlenecks)
4. [Complete Failure Scenario](#complete-failure-scenario)
5. [Summary](#summary)

---

## Overview

The current license selection process has **4 critical bottlenecks** where multiple subscription licenses get reduced to a single license, preventing learners from accessing courses they're entitled to through alternative licenses.

### Architecture Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        Current Architecture                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  License Manager API ─────► Enterprise Access BFF ─────► MFE   │
│   (Returns ALL)           (Selects FIRST)         (Uses FIRST)  │
│                                                                  │
│  [A, B, C]          ───►        [A]          ───►      [A]      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step-by-Step Flow

### Step 1: License Manager Returns ALL Licenses ✅

**File:** `license-manager/license_manager/apps/api/v1/views.py` (Lines 624-770)

The License Manager API correctly returns **all** licenses associated with a learner.

#### Code

```python
class LearnerLicensesViewSet(
    PermissionRequiredForListingMixin,
    ListModelMixin,
    UserDetailsFromJwtMixin,
    viewsets.GenericViewSet
):
    """
    This Viewset allows read operations of all Licenses associated with the email address
    of the requesting user that are associated with a given enterprise customer UUID.

    Query Parameters:
      - enterprise_customer_uuid (UUID string): More or less required, will return an empty list without a valid value.
      This endpoint will filter for License records associated with SubscriptionPlans associated
      with this enterprise customer UUID.

      - active_plans_only (boolean): Defaults to true.  Will filter for only Licenses
      associated with SubscriptionPlans that have `is_active=true` if true.  Will not
      do any filtering based on `is_active` if false.

      - current_plans_only (boolean): Defaults to true.  Will filter for only Licenses
      associated with SubscriptionPlans where the current date is between the plan's
      `start_date` and `expiration_date` (inclusive) if true.  Will not do any filtering
      based on the (start, expiration) date range if false.

    - include_revoked (boolean): Defaults to false.  Will include revoked licenses.

    Example Request:
      GET /api/v1/learner-licenses?enterprise_customer_uuid=the-uuid&active_plans_only=true&current_plans_only=false
    """
```

#### Response Example

```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "uuid": "license-A-uuid",
      "status": "activated",
      "activation_date": "2024-01-15T10:30:00Z",
      "subscription_plan": {
        "uuid": "plan-A-uuid",
        "enterprise_catalog_uuid": "catalog-A-uuid",
        "enterprise_customer_uuid": "acme-corp-uuid",
        "is_active": true,
        "is_current": true,
        "title": "Learning Pathway A",
        "start_date": "2024-01-01",
        "expiration_date": "2024-12-31"
      }
    },
    {
      "uuid": "license-B-uuid",
      "status": "activated",
      "activation_date": "2024-02-01T14:20:00Z",
      "subscription_plan": {
        "uuid": "plan-B-uuid",
        "enterprise_catalog_uuid": "catalog-B-uuid",
        "enterprise_customer_uuid": "acme-corp-uuid",
        "is_active": true,
        "is_current": true,
        "title": "Learning Pathway B",
        "start_date": "2024-01-01",
        "expiration_date": "2024-12-31"
      }
    },
    {
      "uuid": "license-C-uuid",
      "status": "assigned",
      "activation_date": null,
      "subscription_plan": {
        "uuid": "plan-C-uuid",
        "enterprise_catalog_uuid": "catalog-C-uuid",
        "enterprise_customer_uuid": "acme-corp-uuid",
        "is_active": true,
        "is_current": true,
        "title": "Learning Pathway C",
        "start_date": "2024-01-01",
        "expiration_date": "2024-12-31"
      }
    }
  ]
}
```

**Status:** ✅ **Working correctly** - License Manager returns the complete list.

---

### Step 2: BFF Extracts SINGLE License 🚨 BOTTLENECK #1

**File:** `enterprise-access/enterprise_access/apps/bffs/handlers.py` (Lines 262-280)

The BFF receives all licenses but **extracts only the first one** based on priority.

#### Code

```python
def _extract_subscription_license(self, subscription_licenses_by_status):
    """
    Extract subscription licenses from the subscription licenses by status.
    
    🚨 BOTTLENECK: Returns only the FIRST license based on status priority
    """
    license_status_priority_order = [
        LicenseStatuses.ACTIVATED,    # Priority 1: Check activated licenses first
        LicenseStatuses.ASSIGNED,     # Priority 2: Then check assigned licenses
        LicenseStatuses.REVOKED,      # Priority 3: Finally check revoked licenses
    ]
    
    # This generator returns ONLY THE FIRST license it encounters!
    subscription_license = next(
        (
            license
            for status in license_status_priority_order
            for license in subscription_licenses_by_status.get(status, [])
        ),
        None,  # Returns None if no licenses found
    )
    return subscription_license
```

#### What Happens

```
Input:  subscription_licenses_by_status = {
          "activated": [License A, License B],
          "assigned": [License C]
        }

Loop execution:
  1. status = "activated"
  2. Iterate licenses in activated: [License A, License B]
  3. First iteration: license = License A
  4. next() returns License A immediately ❌
  
Output: License A only
Lost:   License B, License C
```

#### Impact

- **License A** is selected (first activated license)
- **License B** is discarded (even though it's also activated!)
- **License C** is ignored (never checked because A was found first)

---

### Step 3: BFF Uses Single License for Enrollment 🚨 BOTTLENECK #2

**File:** `enterprise-access/enterprise_access/apps/bffs/handlers.py` (Lines 579-644)

When enrolling learners in default enterprise courses, only the single selected license is used.

#### Code

```python
def enroll_in_redeemable_default_enterprise_enrollment_intentions(self):
    """
    Enroll in redeemable courses.
    
    🚨 BOTTLENECK: Uses only self.current_activated_license (singular)
    """
    enrollment_statuses = self.default_enterprise_enrollment_intentions.get('enrollment_statuses', {})
    needs_enrollment = enrollment_statuses.get('needs_enrollment', {})
    needs_enrollment_enrollable = needs_enrollment.get('enrollable', [])

    if not needs_enrollment_enrollable:
        # Skip enrolling in default enterprise courses if there are no enrollable courses for which to enroll
        logger.info(
            "No default enterprise enrollment intentions courses for which to enroll "
            "for request user %s and enterprise customer %s",
            self.context.lms_user_id,
            self.context.enterprise_customer_uuid,
        )
        return

    # 🚨 Only check ONE license (the one extracted in Step 2)
    if not self.current_activated_license:
        logger.info(
            "No activated license found for request user %s and enterprise customer %s. "
            "Skipping realization of default enterprise enrollment intentions.",
            self.context.lms_user_id,
            self.context.enterprise_customer_uuid,
        )
        return

    license_uuids_by_course_run_key = {}
    
    # Loop through all courses that need enrollment
    for enrollment_intention in needs_enrollment_enrollable:
        # Get THE ONE license's subscription plan and catalog
        subscription_plan = self.current_activated_license.get('subscription_plan', {})
        subscription_catalog = subscription_plan.get('enterprise_catalog_uuid')
        
        # Get the catalogs that contain this course
        applicable_catalog_to_enrollment_intention = enrollment_intention.get(
            'applicable_enterprise_catalog_uuids'
        )
        
        # Check if THE ONE license's catalog matches this course
        if subscription_catalog in applicable_catalog_to_enrollment_intention:
            course_run_key = enrollment_intention['course_run_key']
            
            # Map this course to THE SAME license UUID
            license_uuids_by_course_run_key[course_run_key] = self.current_activated_license['uuid']

    # Request enrollment realizations
    response_payload = self._request_default_enrollment_realizations(license_uuids_by_course_run_key)
    # ... error handling omitted for brevity
```

#### What Happens

```
Scenario:
  • self.current_activated_license = License A (catalog-A)
  • Courses needing enrollment:
      - Course X (in catalog-B) ❌ Won't match!
      - Course Y (in catalog-A) ✅ Will match
      - Course Z (in catalog-C) ❌ Won't match!

Execution:
  1. Check Course X: catalog-B in License A's catalogs? NO → Skip
  2. Check Course Y: catalog-A in License A's catalogs? YES → Map to License A
  3. Check Course Z: catalog-C in License A's catalogs? NO → Skip

Result:
  • license_uuids_by_course_run_key = {"course-Y-key": "license-A-uuid"}
  • Only Course Y gets enrolled
  • Courses X and Z are ignored (even though License B and C cover them!)
```

#### Impact

- Learner can only auto-enroll in courses covered by **License A's catalog**
- Courses in **catalog-B** are skipped (even though learner has License B!)
- Courses in **catalog-C** are skipped (even though learner has assigned License C!)

---

### Step 4: MFE Extracts Single License Again 🚨 BOTTLENECK #3

**File:** `frontend-app-learner-portal-enterprise/src/components/app/data/services/subsidies/subscriptions.js` (Lines 196-238)

The BFF actually **does send the complete list** in its response, but the MFE immediately reduces it to a single license again.

#### Code

```javascript
export function transformSubscriptionsData({ customerAgreement, subscriptionLicenses }) {
  const { baseSubscriptionsData } = getBaseSubscriptionsData();
  const subscriptionsData = { ...baseSubscriptionsData };

  if (subscriptionLicenses) {
    // ✅ Full list is preserved here
    subscriptionsData.subscriptionLicenses = subscriptionLicenses;
  }
  if (customerAgreement) {
    subscriptionsData.customerAgreement = customerAgreement;
  }

  subscriptionsData.showExpirationNotifications = !(
    customerAgreement?.disableExpirationNotifications || customerAgreement?.hasCustomLicenseExpirationMessagingV2
  );

  // Sort licenses within each license status by whether the associated subscription plans
  // are current; current plans should be prioritized over non-current plans.
  subscriptionsData.subscriptionLicenses = [...subscriptionLicenses].sort((a, b) => {
    const aIsCurrent = a.subscriptionPlan.isCurrent;
    const bIsCurrent = b.subscriptionPlan.isCurrent;
    if (aIsCurrent && bIsCurrent) {
      return 0;
    }
    return aIsCurrent ? -1 : 1;
  });

  // Group licenses by status into a map
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

  // 🚨 BOTTLENECK: Extracts a single subscription license for the user
  const applicableSubscriptionLicense = Object.values(
    subscriptionsData.subscriptionLicensesByStatus
  ).flat()[0];  // <--- [0] takes only the FIRST license!
  
  if (applicableSubscriptionLicense) {
    subscriptionsData.subscriptionLicense = applicableSubscriptionLicense;  // Singular!
    subscriptionsData.subscriptionPlan = applicableSubscriptionLicense.subscriptionPlan;
  }

  return subscriptionsData;
}
```

#### What Happens

```javascript
// Input:
subscriptionLicensesByStatus = {
  activated: [
    { uuid: 'license-A-uuid', subscriptionPlan: {...} },
    { uuid: 'license-B-uuid', subscriptionPlan: {...} }
  ],
  assigned: [
    { uuid: 'license-C-uuid', subscriptionPlan: {...} }
  ]
}

// Step 1: Object.values(...)
[
  [License A, License B],  // activated array
  [License C]              // assigned array
]

// Step 2: .flat()
[License A, License B, License C]

// Step 3: [0]
License A  // ❌ Only the first one!

// Result:
subscriptionsData.subscriptionLicense = License A
subscriptionsData.subscriptionPlan = License A's plan

// Lost:
License B ❌
License C ❌
```

#### Impact

- Even though MFE receives **all licenses** from BFF
- It immediately collapses them to **License A** only
- **License B and C** are discarded for course-level checks
- Data structure has `subscriptionLicenses` (plural) but uses `subscriptionLicense` (singular) everywhere

---

### Step 5: Course Page Checks Single License 🚨 BOTTLENECK #4

**File:** `frontend-app-learner-portal-enterprise/src/components/app/data/utils.js` (Lines 1076-1081)

When checking if a license applies to a specific course, only the singular license is checked.

#### Code: License Applicability Check

```javascript
export function determineSubscriptionLicenseApplicable(subscriptionLicense, catalogsWithCourse) {
  return (
    subscriptionLicense?.status === LICENSE_STATUS.ACTIVATED
    && subscriptionLicense?.subscriptionPlan.isCurrent
    && catalogsWithCourse.includes(subscriptionLicense?.subscriptionPlan.enterpriseCatalogUuid)
  );
}
```

#### Code: Hook Using the Check

**File:** `frontend-app-learner-portal-enterprise/src/components/course/data/hooks/useUserSubsidyApplicableToCourse.js` (Lines 35-108)

```javascript
const useUserSubsidyApplicableToCourse = () => {
  const { courseKey } = useParams();
  
  const {
    data: {
      customerAgreement,
      subscriptionLicense,  // 🚨 Singular license only (from Step 4)
    },
  } = useSubscriptions();
  
  const {
    data: {
      containsContentItems,
      catalogList: catalogsWithCourse,  // Catalogs that contain THIS course
    },
  } = useEnterpriseCustomerContainsContentSuspense([courseKey]);

  // ... other subsidy checks (offers, coupons, learner credit) ...

  // 🚨 Check if THE ONE license applies to THIS course
  const isSubscriptionLicenseApplicable = determineSubscriptionLicenseApplicable(
    subscriptionLicense,  // Only License A is checked!
    catalogsWithCourse,   // e.g., ["catalog-B-uuid"] for this course
  );

  // Get the best subsidy to apply for this course
  const userSubsidyApplicableToCourse = getSubsidyToApplyForCourse({
    applicableSubscriptionLicense: isSubscriptionLicenseApplicable ? subscriptionLicense : null,
    applicableSubsidyAccessPolicy: {
      isPolicyRedemptionEnabled,
      redeemableSubsidyAccessPolicy,
      availableCourseRuns: availableCourseRunsForLearnerCredit,
    },
    applicableCouponCode: findCouponCodeForCourse(couponCodeAssignments, catalogsWithCourse),
    applicableEnterpriseOffer: findEnterpriseOfferForCourse({
      enterpriseOffers: currentEnterpriseOffers,
      catalogsWithCourse,
      coursePrice: courseListPrice,
    }),
  });

  // ... rest of hook ...
  
  return { userSubsidyApplicableToCourse };
};
```

#### What Happens

```
Scenario: User navigates to Course X
  • Course X is in catalog-B
  • catalogsWithCourse = ["catalog-B-uuid"]
  • subscriptionLicense = License A (catalog-A from Step 4)

Execution:
  1. Check: subscriptionLicense?.status === "activated"
     → License A status is "activated" ✅
     
  2. Check: subscriptionLicense?.subscriptionPlan.isCurrent
     → License A plan is current ✅
     
  3. Check: catalogsWithCourse.includes(subscriptionLicense?.subscriptionPlan.enterpriseCatalogUuid)
     → ["catalog-B-uuid"].includes("catalog-A-uuid")
     → FALSE ❌
     
  4. Return: false

Result:
  • isSubscriptionLicenseApplicable = false
  • applicableSubscriptionLicense = null
  • userSubsidyApplicableToCourse might be null (no other subsidies available)
  
UI Shows:
  ⚠️ "You don't have access to this course"
  
Reality:
  ✅ User HAS License B which covers catalog-B!
  😡 But License B was thrown away in Step 4!
```

#### Impact

- User **cannot access Course X** even though they have a valid license (License B)
- The check only validates against **License A** (catalog-A)
- **License B** (catalog-B) was discarded in Step 4
- User sees "no access" message incorrectly

---

## The 4 Bottlenecks

### Summary Table

| # | Location | File | Lines | Method/Function | Problem | Impact |
|---|----------|------|-------|-----------------|---------|--------|
| **1** | Enterprise Access BFF | `handlers.py` | 262-280 | `_extract_subscription_license()` | Uses `next()` to return **first license** only based on status priority | Loses License B, C at backend layer |
| **2** | Enterprise Access BFF | `handlers.py` | 579-644 | `enroll_in_redeemable_default_enterprise_enrollment_intentions()` | Uses `self.current_activated_license` (singular) for **all courses** | Can't auto-enroll in catalog-B or catalog-C courses |
| **3** | Learner Portal MFE | `subscriptions.js` | 233 | `transformSubscriptionsData()` | `Object.values(...).flat()[0]` extracts **first license** only | Loses License B, C at frontend layer |
| **4** | Learner Portal MFE | `utils.js` + `hooks.js` | 1076-1081, 91-96 | `determineSubscriptionLicenseApplicable()` + hook | Checks only **singular `subscriptionLicense`** against course catalogs | Course page can't match License B for catalog-B courses |

---

## Complete Failure Scenario

### Real-World Example: Knotion Learning Pathways

```
┌─────────────────────────────────────────────────────────────────┐
│ Learner: Alice (alice@company.com)                              │
│ Enterprise: Knotion                                             │
│                                                                  │
│ Alice has been assigned 3 learning pathways:                    │
│   1. License A → Catalog A (Leadership Skills)                  │
│   2. License B → Catalog B (Technical Training)                 │
│   3. License C → Catalog C (Compliance Courses)                 │
│                                                                  │
│ Alice activates all 3 licenses via email links                  │
│ Alice tries to access "Python 101" (in Catalog B)               │
└─────────────────────────────────────────────────────────────────┘
```

### Visual Flow

```mermaid
sequenceDiagram
    participant Alice
    participant MFE as Learner Portal<br/>(MFE)
    participant BFF as Enterprise Access<br/>(BFF)
    participant LM as License Manager<br/>(API)

    Note over Alice: Navigates to<br/>/:enterpriseSlug/course/Python-101
    
    Alice->>MFE: GET /course/Python-101
    MFE->>BFF: POST /api/v1/bffs/learner/dashboard/
    
    BFF->>LM: GET /learner-licenses/?enterprise_customer_uuid=knotion
    LM-->>BFF: ✅ {results: [License A, License B, License C]}
    
    Note over BFF: 🚨 Bottleneck #1<br/>_extract_subscription_license()<br/>Returns License A only
    
    Note over BFF: 🚨 Bottleneck #2<br/>enroll_in_redeemable...()<br/>Uses License A for all courses
    
    BFF-->>MFE: Response with all licenses<br/>but BFF context uses only A
    
    Note over MFE: 🚨 Bottleneck #3<br/>transformSubscriptionsData()<br/>Extracts License A only
    
    Note over MFE: Python-101 is in Catalog B<br/>catalogsWithCourse = [catalog-B-uuid]
    
    Note over MFE: 🚨 Bottleneck #4<br/>determineSubscriptionLicenseApplicable()<br/>Checks License A against Catalog B<br/>Result: FALSE ❌
    
    MFE-->>Alice: ⚠️ "You don't have access to this course"
    
    Note over Alice: Expected: Access granted via License B ✅<br/>Reality: Access denied ❌
```

### Step-by-Step Breakdown

#### 1️⃣ License Manager Response (Correct)

```json
{
  "results": [
    {
      "uuid": "license-A-uuid",
      "status": "activated",
      "subscription_plan": {
        "enterprise_catalog_uuid": "catalog-A-uuid",
        "title": "Leadership Skills"
      }
    },
    {
      "uuid": "license-B-uuid",
      "status": "activated",
      "subscription_plan": {
        "enterprise_catalog_uuid": "catalog-B-uuid",
        "title": "Technical Training"
      }
    },
    {
      "uuid": "license-C-uuid",
      "status": "activated",
      "subscription_plan": {
        "enterprise_catalog_uuid": "catalog-C-uuid",
        "title": "Compliance Courses"
      }
    }
  ]
}
```

#### 2️⃣ BFF Processing (Extract First - WRONG)

```python
# _extract_subscription_license() is called
subscription_licenses_by_status = {
    "activated": [License A, License B, License C]
}

# Returns License A (first in activated list)
result = License A  # ❌

# Lost: License B, License C
```

#### 3️⃣ BFF Enrollment Check (Single License - WRONG)

```python
# enroll_in_redeemable_default_enterprise_enrollment_intentions()
current_activated_license = License A  # From Step 2

for course in needs_enrollment:
    subscription_catalog = License A's catalog_uuid  # catalog-A-uuid
    
    # Python-101 is in catalog-B-uuid
    applicable_catalogs = ["catalog-B-uuid"]
    
    if "catalog-A-uuid" in ["catalog-B-uuid"]:  # FALSE ❌
        # Never executes!
        pass
    
# Python-101 is NOT auto-enrolled even though License B covers it!
```

#### 4️⃣ MFE Processing (Extract First Again - WRONG)

```javascript
// transformSubscriptionsData()
subscriptionLicensesByStatus = {
  activated: [License A, License B, License C]
}

// Object.values(...).flat()[0]
const applicableSubscriptionLicense = License A  // ❌

subscriptionsData.subscriptionLicense = License A  // Singular!

// Lost: License B, License C (again!)
```

#### 5️⃣ Course Page Check (Single License - WRONG)

```javascript
// useUserSubsidyApplicableToCourse hook
const subscriptionLicense = License A  // From Step 4
const catalogsWithCourse = ["catalog-B-uuid"]  // Python-101's catalog

// determineSubscriptionLicenseApplicable(License A, ["catalog-B-uuid"])
const result = (
  License A.status === "activated"  // ✅ TRUE
  && License A.subscriptionPlan.isCurrent  // ✅ TRUE
  && ["catalog-B-uuid"].includes("catalog-A-uuid")  // ❌ FALSE
)

// result = false

const userSubsidyApplicableToCourse = null  // No subsidy!
```

#### 6️⃣ Final Result (Access Denied - WRONG)

```
UI Displays:
┌─────────────────────────────────────────────────┐
│  ⚠️ You don't have access to this course        │
│                                                 │
│  Python 101 is not included in your current    │
│  subscription plan.                             │
│                                                 │
│  Please contact your administrator.             │
└─────────────────────────────────────────────────┘

Expected Result:
┌─────────────────────────────────────────────────┐
│  ✅ Enroll in Python 101                        │
│                                                 │
│  This course is included in your                │
│  Technical Training subscription.               │
│                                                 │
│  [Enroll Now]                                   │
└─────────────────────────────────────────────────┘
```

---

## Summary

### The Problem in One Sentence

**"Multiple active licenses are collapsed to a single license at 4 different points in the stack, preventing learners from accessing courses they're entitled to through alternative licenses."**

### Why This Matters

1. **Knotion Use Case:** Learners assigned multiple learning pathways (each with its own catalog) can only access courses from the first pathway
2. **Failed Auto-Enrollment:** Default enterprise courses in non-primary catalogs are never enrolled
3. **Support Burden:** Learners contact support saying "I activated my license but can't access courses" 
4. **Data Inconsistency:** License Manager knows about all licenses, but BFF and MFE ignore most of them
5. **Wasted Licenses:** Enterprises pay for multiple licenses per learner but only one is usable

### The Root Cause

**Architectural assumption:** *"A learner has exactly one subscription license at a time"*

This assumption is baked into:
- Variable naming (`subscription_license` not `subscription_licenses`)
- Data extraction logic (priority-based selection with `next()`)
- Business logic (single license used for all courses)
- Frontend state management (singular license stored and checked)

### The Solution (Proposed in RFC)

**New architecture:** *"A learner may have multiple active licenses; each course is matched to the best applicable license"*

Key changes:
1. **Collection-first contract** (`subscription_licenses` becomes canonical)
2. **Per-course license matching** (check all licenses for each course)
3. **Deterministic selection** (if multiple licenses apply, use consistent tie-breaker)
4. **Feature flag rollout** (gradual migration with backward compatibility)

---

## Related Documentation

- [Multiplex Subscription Licenses RFC](multiplex-subscription-licenses-rfc.md) - Full implementation plan
- [test.txt](../../../../../test.txt) - Original requirements document

---

**Document Version:** 1.0  
**Author:** GitHub Copilot (Analysis based on code in edx-repos workspace)  
**Last Updated:** March 26, 2026
