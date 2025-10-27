"""
Member models.
Comprehensive member management with denomination-specific fields.
"""

from django.db import models
from django.conf import settings


class Member(models.Model):
    """
    Member model with comprehensive fields including denomination-specific data.
    """
    
    # Link to User account
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='member_profile'
    )
    
    # Member Identification
    member_id = models.CharField(max_length=50, unique=True, db_index=True)
    
    # Basic Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    surname = models.CharField(max_length=100, blank=True)  # For compatibility
    other_names = models.CharField(max_length=200, blank=True)
    
    # Contact Information
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    telephone_home = models.CharField(max_length=50, blank=True)
    
    # Address
    address = models.TextField(blank=True)
    postal_address = models.CharField(max_length=255, blank=True)
    residential_house_no = models.CharField(max_length=100, blank=True)
    community = models.CharField(max_length=100, blank=True)
    street = models.CharField(max_length=255, blank=True)
    
    # Personal Details
    gender = models.CharField(
        max_length=10,
        choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')],
        blank=True
    )
    date_of_birth = models.DateField(null=True, blank=True)
    place_of_birth = models.CharField(max_length=200, blank=True)
    home_town = models.CharField(max_length=200, blank=True)
    region = models.CharField(max_length=100, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    
    # Identification
    id_type = models.CharField(max_length=50, blank=True)
    id_no = models.CharField(max_length=100, blank=True)
    
    # Occupation
    occupational_status = models.CharField(max_length=100, blank=True)
    profession = models.CharField(max_length=200, blank=True)
    place_of_work = models.CharField(max_length=255, blank=True)
    
    # Education
    name_of_jhs = models.CharField(max_length=255, blank=True)
    jhs_completion_year = models.CharField(max_length=4, blank=True)
    name_of_shs = models.CharField(max_length=255, blank=True)
    shs_completion_year = models.CharField(max_length=4, blank=True)
    name_of_tertiary = models.CharField(max_length=255, blank=True)
    tertiary_completion_year = models.CharField(max_length=4, blank=True)
    
    # Parents/Guardians
    father_guardian_name = models.CharField(max_length=255, blank=True)
    father_catholic = models.BooleanField(default=False)
    father_parish = models.CharField(max_length=255, blank=True)
    mother_guardian_name = models.CharField(max_length=255, blank=True)
    mother_catholic = models.BooleanField(default=False)
    mother_parish = models.CharField(max_length=255, blank=True)
    
    # Membership
    membership_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('suspended', 'Suspended'),
            ('transferred', 'Transferred'),
        ],
        default='active'
    )
    
    # Family & Relationships (JSON fields)
    family_members = models.JSONField(default=list, blank=True)
    children = models.JSONField(default=list, blank=True)
    
    # Sacraments (JSON field for denomination-specific sacraments)
    sacraments = models.JSONField(default=dict, blank=True)
    
    # Denomination-specific data (JSON field)
    denomination_specific_data = models.JSONField(default=dict, blank=True)
    
    # Additional data
    others = models.JSONField(default=dict, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Engagement Metrics (for analytics)
    last_activity_date = models.DateTimeField(null=True, blank=True)
    engagement_score = models.IntegerField(default=0)
    total_giving = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_volunteer_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    ministries_count = models.IntegerField(default=0)
    events_attended = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'members'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['member_id']),
            models.Index(fields=['email']),
            models.Index(fields=['status']),
            models.Index(fields=['last_name', 'first_name']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.member_id})"
    
    @property
    def full_name(self):
        """Get member's full name."""
        return f"{self.first_name} {self.last_name}"


class MemberWorkflow(models.Model):
    """
    Member workflows for baptism, confirmation, membership, etc.
    """
    
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='workflows')
    
    type = models.CharField(
        max_length=50,
        choices=[
            ('baptism', 'Baptism'),
            ('confirmation', 'Confirmation'),
            ('membership', 'Membership'),
            ('transfer', 'Transfer'),
        ]
    )
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('completed', 'Completed'),
        ],
        default='pending'
    )
    
    steps = models.JSONField(default=list, blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_workflows'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'member_workflows'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.member.full_name} - {self.type} ({self.status})"


class MemberRequest(models.Model):
    """
    Membership application requests.
    For prospective members applying to join the church.
    """
    
    # Personal Information
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    address = models.TextField()
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10)
    marital_status = models.CharField(max_length=20)
    occupation = models.CharField(max_length=255, blank=True)
    
    # Emergency Contact
    emergency_contact = models.JSONField(default=dict)
    
    # Church Experience
    church_experience = models.TextField()
    reason_for_joining = models.TextField()
    how_did_you_hear = models.TextField()
    special_needs = models.TextField(blank=True)
    
    # Skills & Interests
    skills = models.JSONField(default=list)
    interests = models.JSONField(default=list)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='pending'
    )
    
    # Review
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_requests'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'member_requests'
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"{self.name} - {self.status}"
