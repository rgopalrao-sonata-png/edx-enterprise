# edx-enterprise Database Schema

Complete documentation of all database tables and their relationships.

**Last Updated**: March 2026  
**Django Version**: 5.2

---

## Table of Contents

1. [Core Enterprise Models](#core-enterprise-models)
2. [User & Admin Models](#user--admin-models)
3. [Enrollment Models](#enrollment-models)
4. [Catalog Models](#catalog-models)
5. [Configuration Models](#configuration-models)
6. [Group Models](#group-models)
7. [Notification Models](#notification-models)
8. [Consent Models](#consent-models)
9. [Integrated Channel Models](#integrated-channel-models)
10. [Relationship Diagram](#relationship-diagram)

---

## Core Enterprise Models

### 1. `enterprise_enterprisecustomer`

**Purpose**: Represents an enterprise/organization on the platform

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `uuid` | UUIDField | Unique identifier | Unique, Indexed |
| `name` | CharField(255) | Enterprise name | Required |
| `slug` | SlugField(30) | URL-friendly identifier | Unique |
| `active` | BooleanField | Whether enterprise is active | Default: True |
| `site` | ForeignKey | Associated site | FK to django_site |
| `country` | CharField(2) | ISO country code | Optional |
| `hide_course_original_price` | BooleanField | Hide pricing | Default: False |
| `enable_data_sharing_consent` | BooleanField | Require consent | Default: False |
| `enforce_data_sharing_consent` | CharField(25) | Enforcement level | Choices |
| `enable_audit_enrollment` | BooleanField | Allow audit enrollments | Default: False |
| `enable_audit_data_reporting` | BooleanField | Report audit data | Default: False |
| `replace_sensitive_sso_username` | BooleanField | Anonymize SSO usernames | Default: False |
| `enable_portal_code_management_screen` | BooleanField | Portal feature flag | Default: False |
| `enable_portal_reporting_config_screen` | BooleanField | Portal feature flag | Default: False |
| `enable_portal_saml_configuration_screen` | BooleanField | Portal feature flag | Default: False |
| `enable_portal_subscription_management_screen` | BooleanField | Portal feature flag | Default: False |
| `enable_learner_portal` | BooleanField | Enable learner portal | Default: False |
| `enable_learner_portal_offers` | BooleanField | Show offers | Default: False |
| `enable_integrated_customer_learner_portal_search` | BooleanField | Integrated search | Default: False |
| `enable_analytics_screen` | BooleanField | Analytics feature | Default: False |
| `enable_slug_login` | BooleanField | Allow slug-based login | Default: False |
| `contact_email` | EmailField | Admin contact email | Optional |
| `sender_alias` | CharField(255) | Email sender alias | Optional |
| `reply_to` | EmailField | Email reply-to address | Optional |
| `customer_type` | ForeignKey | Type of customer | FK to EnterpriseCustomerType |
| `auth_org_id` | CharField(80) | External auth org ID | Optional |
| `enable_universal_link` | BooleanField | Universal link feature | Default: False |
| `enable_browse_and_request` | BooleanField | Browse/request feature | Default: False |
| `enable_generation_of_api_credentials` | BooleanField | API creds feature | Default: False |
| `modified` | DateTimeField | Last modified timestamp | Auto |
| `created` | DateTimeField | Creation timestamp | Auto |

**Indexes**:
- `uuid` (unique)
- `slug` (unique)
- `site_id`
- `customer_type_id`

**Related Tables**:
- EnterpriseCustomerUser (1-to-Many)
- EnterpriseCustomerCatalog (1-to-Many)
- EnterpriseCustomerAdmin (1-to-Many)
- EnterpriseGroup (1-to-Many)

---

### 2. `enterprise_enterprisecustomertype`

**Purpose**: Categorizes enterprise customers

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `uuid` | UUIDField | Unique identifier | Unique |
| `name` | CharField(25) | Type name | Required |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

**Values**: `business`, `nonprofit`, `government`, etc.

---

## User & Admin Models

### 3. `enterprise_enterprisecustomeruser`

**Purpose**: Links users to enterprise customers

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `uuid` | UUIDField | Unique identifier | Unique, Indexed |
| `enterprise_customer` | ForeignKey | Associated enterprise | FK to EnterpriseCustomer |
| `user_id` | PositiveIntegerField | LMS user ID | Required, Indexed |
| `active` | BooleanField | Whether link is active | Default: True |
| `linked` | BooleanField | Whether user is linked | Default: True |
| `is_relinkable` | BooleanField | Can be relinked | Default: True |
| `invite_key` | ForeignKey | Invitation used | FK to EnterpriseCustomerInviteKey, Null |
| `should_inactivate_other_customers` | BooleanField | Inactivate others | Default: False |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

**Unique Together**: (`enterprise_customer`, `user_id`)

**Indexes**:
- `uuid`
- `user_id`
- `enterprise_customer_id`

---

### 4. `enterprise_pendingenterprisecustomeruser`

**Purpose**: Temporary record for users not yet in LMS

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `uuid` | UUIDField | Unique identifier | Unique |
| `enterprise_customer` | ForeignKey | Associated enterprise | FK to EnterpriseCustomer |
| `user_email` | EmailField | Email address | Required |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

**Unique Together**: (`enterprise_customer`, `user_email`)

---

### 5. `enterprise_enterprisecustomeradmin`

**Purpose**: Admin users for an enterprise

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `uuid` | UUIDField | Unique identifier | Unique |
| `enterprise_customer` | ForeignKey | Associated enterprise | FK to EnterpriseCustomer |
| `user_id` | PositiveIntegerField | LMS user ID | Required |
| `active` | BooleanField | Whether admin is active | Default: True |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

**Unique Together**: (`enterprise_customer`, `user_id`)

**Indexes**:
- `enterprise_customer_id`
- `user_id`

---

### 6. `enterprise_pendingenterprisecustomeradminuser`

**Purpose**: Pending admin invitations

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `uuid` | UUIDField | Unique identifier | Unique |
| `enterprise_customer` | ForeignKey | Associated enterprise | FK to EnterpriseCustomer |
| `user_email` | EmailField | Email address | Required |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

**Unique Together**: (`enterprise_customer`, `user_email`)

---

## Enrollment Models

### 7. `enterprise_enterprisecourseenrollment`

**Purpose**: Tracks enterprise-sponsored course enrollments

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `uuid` | UUIDField | Unique identifier | Unique |
| `enterprise_customer_user` | ForeignKey | Associated user | FK to EnterpriseCustomerUser |
| `course_id` | CharField(255) | Course identifier | Required |
| `saved_for_later` | BooleanField | Saved for later | Default: False |
| `source` | ForeignKey | Enrollment source | FK to EnterpriseEnrollmentSource, Null |
| `unenrolled` | BooleanField | Whether unenrolled | Default: False |
| `unenrolled_at` | DateTimeField | Unenrollment timestamp | Null |
| `marked_done` | BooleanField | Marked as complete | Default: False |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

**Unique Together**: (`enterprise_customer_user`, `course_id`)

**Indexes**:
- `uuid`
- `enterprise_customer_user_id`
- `course_id`
- `source_id`

---

### 8. `enterprise_enterpriseenrollmentsource`

**Purpose**: Tracks where enrollments originated

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `uuid` | UUIDField | Unique identifier | Unique |
| `name` | CharField(64) | Source name | Required, Unique |
| `slug` | SlugField(30) | URL-friendly slug | Unique |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

**Common Values**: 
- `enterprise_enrollment_api`
- `enterprise_customer_bulk_enrollment`
- `enrollment_task`
- `offer_redemption`

---

### 9. `enterprise_pendingenrollment`

**Purpose**: Enrollments for users not yet in LMS

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `user` | ForeignKey | Pending user | FK to PendingEnterpriseCustomerUser |
| `course_id` | CharField(255) | Course identifier | Required |
| `course_mode` | CharField(25) | Enrollment mode | Required |
| `cohort_name` | CharField(127) | Cohort name | Optional |
| `discount_percentage` | DecimalField | Discount amount | 0-100 |
| `sales_force_id` | CharField(255) | Salesforce opportunity ID | Optional |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

**Unique Together**: (`user`, `course_id`)

---

### 10. `enterprise_enterprisecourseentitlement`

**Purpose**: Tracks enterprise-sponsored course entitlements

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `uuid` | UUIDField | Unique identifier | Unique |
| `enterprise_customer_user` | ForeignKey | Associated user | FK to EnterpriseCustomerUser |
| `entitlement_id` | PositiveIntegerField | LMS entitlement ID | Required, Unique |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

---

### 11. `enterprise_enterprisefulfillmentsource`

**Purpose**: Tracks subsidy fulfillment sources

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `uuid` | UUIDField | Unique identifier | Unique |
| `slug` | SlugField(255) | Source slug | Unique |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

---

## Catalog Models

### 12. `enterprise_enterprisecatalogquery`

**Purpose**: Content discovery queries for enterprise catalogs

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `uuid` | UUIDField | Unique identifier | Unique |
| `content_filter` | JSONField | Query filter definition | Required |
| `title` | CharField(255) | Query title | Optional |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

**Example content_filter**:
```json
{
  "content_type": "course",
  "level_type": ["Intermediate", "Advanced"],
  "aggregation_key": ["org:MITx"]
}
```

---

### 13. `enterprise_enterprisecustomercatalog`

**Purpose**: Associates catalogs with enterprise customers

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `uuid` | UUIDField | Unique identifier | Unique, Indexed |
| `title` | CharField(255) | Catalog title | Required |
| `enterprise_customer` | ForeignKey | Associated enterprise | FK to EnterpriseCustomer |
| `content_filter` | JSONField | Catalog filter | Optional |
| `enabled_course_modes` | JSONField | Allowed modes | Default: [] |
| `publish_audit_enrollment_urls` | BooleanField | Publish audit URLs | Default: False |
| `enterprise_catalog_query` | ForeignKey | Associated query | FK to EnterpriseCatalogQuery, Null |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

**Indexes**:
- `uuid`
- `enterprise_customer_id`
- `enterprise_catalog_query_id`

---

## Configuration Models

### 14. `enterprise_enterprisecustomerbrandingconfiguration`

**Purpose**: Branding/theming for enterprise portals

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `enterprise_customer` | OneToOneField | Associated enterprise | FK to EnterpriseCustomer |
| `logo` | ImageField | Enterprise logo | Optional |
| `primary_color` | CharField(10) | Hex color code | Optional |
| `secondary_color` | CharField(10) | Hex color code | Optional |
| `tertiary_color` | CharField(10) | Hex color code | Optional |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

---

### 15. `enterprise_enterprisecustomeridentityprovider`

**Purpose**: SSO identity provider configuration

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `enterprise_customer` | ForeignKey | Associated enterprise | FK to EnterpriseCustomer |
| `provider_id` | SlugField(50) | IDP identifier | Required, Unique |
| `default_provider` | BooleanField | Is default IDP | Default: False |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

---

### 16. `enterprise_enterprisecustomerssoconfiguration`

**Purpose**: SSO configuration details (SAML, OAuth)

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `uuid` | UUIDField | Unique identifier | Unique |
| `enterprise_customer` | ForeignKey | Associated enterprise | FK to EnterpriseCustomer |
| `active` | BooleanField | Configuration active | Default: True |
| `identity_provider` | CharField(100) | IDP type | Choices |
| `metadata_url` | URLField | SAML metadata URL | Optional |
| `metadata_xml` | TextField | SAML metadata XML | Optional |
| `entity_id` | CharField(255) | SAML entity ID | Optional |
| `sso_url` | URLField | SSO endpoint URL | Optional |
| `public_key` | TextField | X.509 certificate | Optional |
| `is_removed` | BooleanField | Soft delete flag | Default: False |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

---

### 17. `enterprise_enterprisecustomerreportingconfiguration`

**Purpose**: Data reporting configuration

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `uuid` | UUIDField | Unique identifier | Unique |
| `enterprise_customer` | ForeignKey | Associated enterprise | FK to EnterpriseCustomer |
| `active` | BooleanField | Configuration active | Default: True |
| `delivery_method` | CharField(20) | Delivery type | Choices: email, sftp |
| `email` | EmailField | Report recipient email | Optional |
| `frequency` | CharField(20) | Report frequency | Choices: daily, weekly, monthly |
| `day_of_month` | SmallIntegerField | Day for monthly reports | 1-31, Optional |
| `day_of_week` | SmallIntegerField | Day for weekly reports | 0-6, Optional |
| `hour_of_day` | SmallIntegerField | Hour for delivery | 0-23 |
| `sftp_hostname` | CharField(256) | SFTP server | Optional |
| `sftp_port` | PositiveIntegerField | SFTP port | Default: 22 |
| `sftp_username` | CharField(256) | SFTP username | Optional |
| `sftp_password` | CharField(256) | Encrypted SFTP password | Optional |
| `sftp_file_path` | CharField(256) | Remote file path | Optional |
| `data_type` | CharField(20) | Report data type | Choices |
| `report_type` | CharField(20) | Report format | Choices |
| `pgp_encryption_key` | TextField | PGP public key | Optional |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

---

### 18. `enterprise_enrollmentnotificationemailtemplate`

**Purpose**: Custom email templates for enrollments

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `enterprise_customer` | ForeignKey | Associated enterprise | FK to EnterpriseCustomer |
| `plaintext_template` | TextField | Plain text template | Required |
| `html_template` | TextField | HTML template | Required |
| `subject_line` | CharField(100) | Email subject | Required |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

---

## Group Models

### 19. `enterprise_enterprisegroup`

**Purpose**: Sub-groups within an enterprise (departments, teams)

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `uuid` | UUIDField | Unique identifier | Unique, Indexed |
| `enterprise_customer` | ForeignKey | Associated enterprise | FK to EnterpriseCustomer |
| `name` | CharField(25) | Group name | Required |
| `applies_to_all_contexts` | BooleanField | Global group | Default: False |
| `is_removed` | BooleanField | Soft delete flag | Default: False |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

---

### 20. `enterprise_enterprisegroupmembership`

**Purpose**: Members of enterprise groups

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `uuid` | UUIDField | Unique identifier | Unique |
| `group` | ForeignKey | Associated group | FK to EnterpriseGroup |
| `enterprise_customer_user` | ForeignKey | Member user | FK to EnterpriseCustomerUser, Null |
| `pending_enterprise_customer_user` | ForeignKey | Pending member | FK to PendingEnterpriseCustomerUser, Null |
| `status` | CharField(25) | Membership status | Choices |
| `activated_at` | DateTimeField | Activation timestamp | Null |
| `removed_at` | DateTimeField | Removal timestamp | Null |
| `errored_at` | DateTimeField | Error timestamp | Null |
| `is_removed` | BooleanField | Soft delete flag | Default: False |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

**Status Choices**: `pending`, `accepted`, `rejected`, `removed`

---

## Notification Models

### 21. `enterprise_adminnotification`

**Purpose**: Admin notifications/announcements

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `uuid` | UUIDField | Unique identifier | Unique |
| `title` | CharField(255) | Notification title | Required |
| `text` | TextField | Notification content | Required |
| `is_active` | BooleanField | Currently active | Default: True |
| `start_date` | DateTimeField | Start showing | Required |
| `expiration_date` | DateTimeField | Stop showing | Optional |
| `admin_notification_filter` | ForeignKey | Target filter | FK to AdminNotificationFilter, Null |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

---

### 22. `enterprise_adminnotificationread`

**Purpose**: Tracks which admins have read notifications

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `enterprise_customer_user` | ForeignKey | Reader | FK to EnterpriseCustomerUser |
| `admin_notification` | ForeignKey | Notification | FK to AdminNotification |
| `is_read` | BooleanField | Read status | Default: False |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

**Unique Together**: (`enterprise_customer_user`, `admin_notification`)

---

### 23. `enterprise_adminnotificationfilter`

**Purpose**: Filters for targeting notifications

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `filter` | JSONField | Filter criteria | Required |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

---

## Consent Models

### 24. `consent_datasharingconsent`

**Purpose**: Tracks user consent for data sharing

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `enterprise_customer` | ForeignKey | Associated enterprise | FK to EnterpriseCustomer |
| `username` | CharField(255) | User username | Required |
| `course_id` | CharField(255) | Course identifier | Required |
| `granted` | NullBooleanField | Consent status | Null/True/False |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

**Unique Together**: (`enterprise_customer`, `username`, `course_id`)

---

### 25. `consent_datasharingconsenttextoverrides`

**Purpose**: Custom consent text per enterprise

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `enterprise_customer` | OneToOneField | Associated enterprise | FK to EnterpriseCustomer |
| `page_title` | TextField | Custom page title | Optional |
| `left_sidebar_text` | TextField | Left sidebar content | Optional |
| `top_paragraph` | TextField | Top paragraph text | Optional |
| `agreement_text` | TextField | Agreement text | Optional |
| `continue_text` | TextField | Continue button text | Optional |
| `abort_text` | TextField | Abort button text | Optional |
| `policy_dropdown_header` | TextField | Policy header | Optional |
| `policy_paragraph` | TextField | Policy text | Optional |
| `confirmation_alert_prompt` | TextField | Confirmation prompt | Optional |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

---

## Integrated Channel Models

### 26. `integrated_channel_contentmetadataitemtransmission`

**Purpose**: Tracks content metadata sync to external systems

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `enterprise_customer` | ForeignKey | Associated enterprise | FK to EnterpriseCustomer |
| `integrated_channel_code` | CharField(30) | Channel identifier | Required |
| `content_id` | CharField(255) | Content identifier | Required |
| `channel_metadata` | JSONField | Metadata sent | Required |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

**Integrated Channels**: SAP SuccessFactors, Cornerstone, Degreed, Canvas, Blackboard, Moodle, XAPI

---

### 27. `integrated_channel_learnerdatatransmissionaudit`

**Purpose**: Audit log for learner data transmissions

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `enterprise_customer_uuid` | UUIDField | Enterprise UUID | Required |
| `user_id` | PositiveIntegerField | LMS user ID | Required |
| `course_id` | CharField(255) | Course identifier | Required |
| `course_completed` | BooleanField | Completion status | Default: False |
| `completed_timestamp` | DateTimeField | Completion time | Optional |
| `grade` | CharField(100) | Final grade | Optional |
| `total_hours` | FloatField | Hours spent | Optional |
| `status` | CharField(100) | Transmission status | Required |
| `error_message` | TextField | Error details | Optional |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

---

## Additional Models

### 28. `enterprise_defaultenterpriseenrollmentintention`

**Purpose**: Tracks enrollment intentions for unauthenticated users

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `uuid` | UUIDField | Unique identifier | Unique |
| `course_id` | CharField(255) | Course identifier | Required |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |
| `is_removed` | BooleanField | Soft delete | Default: False |

---

### 29. `enterprise_enterprisecustomerinvitekey`

**Purpose**: Invitation keys for enterprise onboarding

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `uuid` | UUIDField | Unique identifier | Unique, Indexed |
| `enterprise_customer` | ForeignKey | Associated enterprise | FK to EnterpriseCustomer |
| `usage_count` | PositiveIntegerField | Times used | Default: 0 |
| `usage_limit` | PositiveIntegerField | Maximum uses | Required |
| `expiration_date` | DateTimeField | Expiry date | Optional |
| `is_active` | BooleanField | Currently valid | Default: True |
| `is_removed` | BooleanField | Soft delete | Default: False |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

---

### 30. `enterprise_chatgptresponse`

**Purpose**: Caches ChatGPT API responses

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | AutoField | Primary key | PK |
| `uuid` | UUIDField | Unique identifier | Unique |
| `prompt_hash` | CharField(64) | Hash of prompt | Indexed |
| `prompt_text` | TextField | Original prompt | Required |
| `response` | JSONField | ChatGPT response | Required |
| `created` | DateTimeField | Creation timestamp | Auto |
| `modified` | DateTimeField | Last modified timestamp | Auto |

---

## Relationship Diagram

```
EnterpriseCustomer (1) ──────── (M) EnterpriseCustomerUser
       │                               │
       │                               └─── (1) User (LMS)
       │
       ├────── (M) EnterpriseCustomerAdmin
       │
       ├────── (M) PendingEnterpriseCustomerUser
       │
       ├────── (M) PendingEnterpriseCustomerAdminUser
       │
       ├────── (M) EnterpriseCustomerCatalog
       │              │
       │              └─── (1) EnterpriseCatalogQuery
       │
       ├────── (M) EnterpriseGroup
       │              │
       │              └─── (M) EnterpriseGroupMembership
       │                         │
       │                         ├─── (1) EnterpriseCustomerUser
       │                         └─── (1) PendingEnterpriseCustomerUser
       │
       ├────── (1) EnterpriseCustomerBrandingConfiguration
       │
       ├────── (M) EnterpriseCustomerIdentityProvider
       │
       ├────── (M) EnterpriseCustomerSsoConfiguration
       │
       ├────── (M) EnterpriseCustomerReportingConfiguration
       │
       ├────── (1) EnrollmentNotificationEmailTemplate
       │
       └────── (M) DataSharingConsent (via consent app)

EnterpriseCustomerUser (1) ──────── (M) EnterpriseCourseEnrollment
                                           │
                                           └─── (1) EnterpriseEnrollmentSource

EnterpriseCustomerUser (1) ──────── (M) EnterpriseCourseEntitlement

PendingEnterpriseCustomerUser (1) ── (M) PendingEnrollment
```

---

## Key Indexes

### Performance-Critical Indexes

| Table | Index | Purpose |
|-------|-------|---------|
| `enterprise_enterprisecustomer` | `uuid` | UUID lookups |
| `enterprise_enterprisecustomer` | `slug` | Slug-based lookups |
| `enterprise_enterprisecustomeruser` | `uuid` | UUID lookups |
| `enterprise_enterprisecustomeruser` | `user_id` | LMS user lookups |
| `enterprise_enterprisecustomeruser` | `(enterprise_customer_id, user_id)` | Unique constraint |
| `enterprise_enterprisecourseenrollment` | `uuid` | UUID lookups |
| `enterprise_enterprisecourseenrollment` | `course_id` | Course lookups |
| `enterprise_enterprisecourseenrollment` | `(enterprise_customer_user_id, course_id)` | Unique constraint |
| `enterprise_enterprisecustomercatalog` | `uuid` | UUID lookups |
| `enterprise_enterprisegroup` | `uuid` | UUID lookups |

---

## Common Query Patterns

### Get Enterprise by Slug
```python
enterprise = EnterpriseCustomer.objects.get(slug='acme-corp')
```

### Get User's Enterprises
```python
user_enterprises = EnterpriseCustomerUser.objects.filter(
    user_id=user.id,
    active=True
).select_related('enterprise_customer')
```

### Get Enterprise Enrollments
```python
enrollments = EnterpriseCourseEnrollment.objects.filter(
    enterprise_customer_user__enterprise_customer=enterprise,
    unenrolled=False
).select_related('enterprise_customer_user__user')
```

### Check Admin Permissions
```python
is_admin = EnterpriseCustomerAdmin.objects.filter(
    enterprise_customer=enterprise,
    user_id=user.id,
    active=True
).exists()
```

---

## Database Migrations

**Location**: `enterprise/migrations/`

**Total Migrations**: 200+ (as of March 2026)

**Key Migration Points**:
- 0001: Initial enterprise models
- 0050: Added catalog queries
- 0100: SSO configuration
- 0150: Enterprise groups
- 0180: Admin invite functionality
- 0200+: Current state

---

## Notes

1. **Soft Deletes**: Models with `is_removed` field use soft delete pattern
2. **UUIDs**: Most models use UUID for external references
3. **Timestamps**: All models have `created` and `modified` via TimeStampedModel
4. **JSON Fields**: Used for flexible configuration (catalogs, notifications, metadata)
5. **Foreign Keys**: Most use `on_delete=CASCADE` unless specified otherwise

---

**Document Version**: 1.0  
**Last Updated**: March 2026  
**Maintainer**: edx-enterprise team
