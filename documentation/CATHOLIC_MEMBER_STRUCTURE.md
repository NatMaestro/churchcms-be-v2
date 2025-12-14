# 📖 Catholic Member Data Structure

## Overview

Catholic members have extensive denomination-specific data including sacraments, family information, education history, and more. This data is stored in the `denomination_specific_data` JSONField of the `Member` model.

---

## Backend Member Model Mapping

### Core Fields (Direct Model Fields)

```python
{
    "member_id": "2",                    # CharField
    "first_name": "Mildred",             # CharField
    "surname": "Aikins",                 # CharField
    "other_names": "Aba",                # CharField
    "gender": "Female",                  # CharField (choices)
    "date_of_birth": "1987-10-11",       # DateField
    "email": "mild.aikins@gmail.com",    # EmailField
    "phone": "+233242184957...",         # CharField
    "status": "active",                  # CharField (choices)
    "membership_date": "2025-10-20",     # DateField

    # Address fields
    "address": "P.O.Box CO55, Tema",     # TextField
    "postal_address": "P.O.Box CO55, Tema",  # CharField
    "telephone_home": "",                # CharField

    # Location
    "place_of_birth": "Tema",            # CharField
    "nationality": "Ghanaian",           # CharField
}
```

### Denomination-Specific Data (JSONField)

All Catholic-specific data goes into `denomination_specific_data`:

```python
{
    "denomination": "Catholic",

    # Residence
    "residential_house_no": "I/K/123",
    "community": "One",
    "street": "Padmore",
    "home_town": "Abrem-Agona",
    "region": "Central Region",

    # Identification
    "id_type": "Voter's ID",
    "id_no": "1830026868",

    # Family Information
    "father_guardian_name": "Mr. Joseph Hanson Leo Aikins",
    "father_catholic": False,
    "father_parish": "OLAM",
    "mother_guardian_name": "Ms. Rose Dadzie",
    "mother_catholic": False,
    "mother_parish": "",

    # Children
    "children": [
        {"name": "Rose Dadzie"}
    ],

    # Education History
    "name_of_jhs": "Christian Vertical Centre",
    "jhs_completion_year": "",
    "name_of_shs": "OLAM Senior High School",
    "shs_completion_year": "",
    "name_of_tertiary": "Accra Polytechnic, GIMPA",
    "tertiary_completion_year": "",

    # Work
    "place_of_work": "Tema",

    # Catholic Specific
    "bcc_name": "Site 5 and 10",  # Basic Christian Community
    "marital_status": "Single",

    # Additional Notes
    "family_members": [],
    "notes": ""
}
```

### Sacraments (Separate JSONField)

The `sacraments` field in the Member model stores:

```python
{
    "baptism": {
        "date": "11th Oct. 1987",
        "nlb": "5074",              # Number in Baptism Register
        "parish": "OLAM",
        "god_parent": "Comfort Atsu"
    },
    "holy_communion": {
        "date": "29th Mar. 1997",
        "nlc": "2459",              # Number in Communion Register
        "parish": ""
    },
    "confirmation": {
        "date": "18th Nov. 2001",
        "nlc": "",
        "parish": "",
        "god_parent": ""
    },
    "reconciliation": {},           # First Confession
    "anointing_of_sick": {},
    "holy_orders": {
        "order_type": "deacon"      # deacon, priest, bishop
    },
    "matrimony": {
        "parish": "",
        "spouse_name": "",
        "marital_status": "Single",
        "bcc_name": "Site 5 and 10",
        "spouse_church": "",
        "customary_marriage_date": "1st Jan. 1970",
        "customary_marriage_place": "",
        "ordinance_marriage_date": "1st Jan. 1970",
        "ordinance_marriage_place": "",
        "holy_matrimony": "1st Jan. 1970",
        "holy_matrimony_parish": "",
        "holy_matrimony_nlm": ""    # Number in Marriage Register
    }
}
```

---

## API Response Format

### GET `/api/v1/members/{id}/`

```json
{
  "id": 2,
  "member_id": "2",
  "first_name": "Mildred",
  "surname": "Aikins",
  "other_names": "Aba",
  "full_name": "Mildred Aba Aikins",
  "gender": "Female",
  "date_of_birth": "1987-10-11",
  "email": "mild.aikins@gmail.com",
  "phone": "+233242184957, 0507884442, 0205797827",
  "status": "active",
  "membership_date": "2025-10-20",
  "address": "P.O.Box CO55, Tema",
  "postal_address": "P.O.Box CO55, Tema",
  "telephone_home": "",
  "place_of_birth": "Tema",
  "nationality": "Ghanaian",
  "created_at": "2025-10-20T19:44:38.384Z",
  "updated_at": "2025-10-20T19:44:38.384Z",

  "sacraments": {
    "baptism": {
      "date": "11th Oct. 1987",
      "nlb": "5074",
      "parish": "OLAM",
      "god_parent": "Comfort Atsu"
    },
    "holy_communion": {
      "date": "29th Mar. 1997",
      "nlc": "2459"
    },
    "confirmation": {
      "date": "18th Nov. 2001"
    },
    "matrimony": {
      "bcc_name": "Site 5 and 10",
      "marital_status": "Single"
    }
  },

  "denomination_specific_data": {
    "denomination": "Catholic",
    "residential_house_no": "I/K/123",
    "community": "One",
    "street": "Padmore",
    "home_town": "Abrem-Agona",
    "region": "Central Region",
    "id_type": "Voter's ID",
    "id_no": "1830026868",
    "father_guardian_name": "Mr. Joseph Hanson Leo Aikins",
    "father_catholic": false,
    "father_parish": "OLAM",
    "mother_guardian_name": "Ms. Rose Dadzie",
    "mother_catholic": false,
    "children": [{ "name": "Rose Dadzie" }],
    "name_of_jhs": "Christian Vertical Centre",
    "name_of_shs": "OLAM Senior High School",
    "name_of_tertiary": "Accra Polytechnic, GIMPA",
    "place_of_work": "Tema",
    "bcc_name": "Site 5 and 10"
  }
}
```

---

## Other Denominations

### Pentecostal/Charismatic

```python
denomination_specific_data = {
    "denomination": "Pentecostal",
    "home_cell_group": "Zone A",
    "spiritual_gifts": ["prophecy", "healing"],
    "baptism_type": "water",  # water, spirit, both
    "speaking_in_tongues": True,
    "ministry_involvement": ["choir", "ushering"]
}
```

### Presbyterian/Methodist

```python
denomination_specific_data = {
    "denomination": "Presbyterian",
    "presbytery": "Accra",
    "congregation": "Trinity",
    "elder_status": "ruling_elder",  # ruling_elder, teaching_elder
    "baptism_mode": "infant",  # infant, believer
    "confirmation_date": "2001-11-18"
}
```

---

## Frontend Integration

### Displaying Catholic Member Data

```typescript
interface CatholicMemberData {
  // Core fields
  id: number;
  memberId: string;
  firstName: string;
  surname: string;
  email: string;

  // Sacraments
  sacraments: {
    baptism?: {
      date: string;
      nlb: string;
      parish: string;
      godParent: string;
    };
    holyCommunion?: {
      date: string;
      nlc: string;
    };
    confirmation?: {
      date: string;
      godParent?: string;
    };
    matrimony?: {
      maritalStatus: string;
      bccName: string;
      spouseName?: string;
    };
  };

  // Catholic-specific data
  denominationSpecificData: {
    denomination: "Catholic";
    residentialHouseNo?: string;
    community?: string;
    homeTown?: string;
    bccName?: string;
    fatherGuardianName?: string;
    motherGuardianName?: string;
    children?: Array<{ name: string }>;
    // ... other fields
  };
}
```

---

## Database Query Examples

### Get all members with specific sacrament

```python
# Get all members who have been confirmed
from apps.members.models import Member

confirmed_members = Member.objects.filter(
    sacraments__confirmation__date__isnull=False
)

# Get members from specific BCC
bcc_members = Member.objects.filter(
    denomination_specific_data__bcc_name="Site 5 and 10"
)

# Get members by sacrament register number
member = Member.objects.filter(
    sacraments__baptism__nlb="5074"
).first()
```

---

## Validation Rules

### Catholic Member Validation

1. **Baptism** - Required for Catholic members
2. **Holy Communion** - Should have Baptism first
3. **Confirmation** - Should have Holy Communion first
4. **Matrimony** - Only for married members
5. **Holy Orders** - Only for ordained members (deacon, priest, bishop)

### Frontend Validation

```typescript
const validateCatholicMember = (data: CatholicMemberData) => {
  // Check baptism date before communion
  if (data.sacraments.holyCommunion?.date && !data.sacraments.baptism?.date) {
    throw new Error("Holy Communion requires Baptism first");
  }

  // Check communion date before confirmation
  if (
    data.sacraments.confirmation?.date &&
    !data.sacraments.holyCommunion?.date
  ) {
    throw new Error("Confirmation requires Holy Communion first");
  }
};
```

---

## Notes

1. **Flexibility**: The `denomination_specific_data` JSONField allows each denomination to store their unique requirements
2. **Extensibility**: New sacraments or fields can be added without database migrations
3. **Validation**: Frontend and backend should validate denomination-specific requirements
4. **Reporting**: Sacrament registers can be generated by querying the `sacraments` field
5. **Privacy**: Some fields (like marital status, children) should have appropriate access controls

---

**This structure supports the full Catholic member lifecycle from baptism through all sacraments!** ⛪





