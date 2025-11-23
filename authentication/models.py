from django.db import models
from django.contrib.auth.models import AbstractUser,BaseUserManager,PermissionsMixin


class CustomUserManager(BaseUserManager):
    def create_user(self,username,first_name,last_name,email,password=None,**extra_fileds):
        if not username:
            raise ValueError("Mobile Number (username) is require")
        email=self.normalize_email(email)
        user=self.model(username=username,first_name=first_name,last_name=last_name,email=email,**extra_fileds)
        user.set_password(password)
        user.save(using=self._db)
        return user
    def create_superuser(self,username,first_name,last_name,email,password=None,**extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(username, first_name, last_name, email, password, **extra_fields)

class User(AbstractUser,PermissionsMixin):
    username = models.CharField(max_length=12,unique=True)  #Mobile Number
    email=models.EmailField(unique=True,blank=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    is_user_verified= models.BooleanField(default=False)
    
    # Profile fields
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    initiation_date = models.DateField(blank=True, null=True)
    
    # QR Code fields
    qr_token = models.CharField(max_length=64, unique=True, blank=True, null=True)
    qr_token_created_at = models.DateTimeField(blank=True, null=True)

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['first_name','last_name','email']

    objects = CustomUserManager()


    def __str__(self):
        return f"{self.first_name} {self.last_name} {self.username} "








