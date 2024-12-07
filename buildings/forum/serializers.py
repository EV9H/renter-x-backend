from rest_framework import serializers
from .models import Category, Post, Comment, Tag, BuildingReference, PostDraft, Building
from buildings.serializers import BuildingSerializer
from django.contrib.auth import get_user_model
from django.utils.html import strip_tags

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        read_only_fields = ['email']

class CategorySerializer(serializers.ModelSerializer):
    published_posts_count = serializers.IntegerField(read_only=True)
    active_posts_count = serializers.IntegerField(read_only=True)
    latest_post_date = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description',
            'published_posts_count', 'active_posts_count',
            'latest_post_date'
        ]
        read_only_fields = ['slug']

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'description', 'usage_count']
        read_only_fields = ['slug', 'usage_count']

class BuildingReferenceSerializer(serializers.ModelSerializer):
    building = BuildingSerializer(read_only=True)
    building_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = BuildingReference
        fields = ['id', 'building', 'building_id', 'reference_type', 'context']

class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = ['id', 'content', 'author', 'parent', 'like_count', 
                 'created_at', 'updated_at', 'replies','post']
        read_only_fields = ['author', 'like_count','post']

    def get_replies(self, obj):
        if not hasattr(obj, 'replies'):
            return []
        serializer = CommentSerializer(obj.replies.all(), many=True)
        return serializer.data
    def create(self, validated_data):
        request = self.context.get('request')
        post = self.context.get('post')
        
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Must be authenticated to comment")
        
        if not post:
            raise serializers.ValidationError("Post is required")

        validated_data['author'] = request.user
        validated_data['post'] = post
        
        return super().create(validated_data)


class PostListSerializer(serializers.ModelSerializer):
    """Serializer for listing posts with minimal information"""
    author = UserSerializer(read_only=True)
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        required=True
    )
    tags = TagSerializer(many=True, read_only=True)
    comment_count = serializers.IntegerField(read_only=True)
    excerpt = serializers.SerializerMethodField()
    category_details = CategorySerializer(source='category', read_only=True) 
    class Meta:
        model = Post
        fields = ['id', 'title', 'slug', 'author', 'category', 'tags', 
                 'status', 'view_count', 'like_count', 'is_pinned','category_details',
                 'created_at', 'last_activity_at', 'comment_count', 'excerpt']
        read_only_fields = ['slug', 'view_count', 'like_count']

    def get_excerpt(self, obj):
        """Return a plain text excerpt of the post content"""
        text = strip_tags(obj.content)  # Remove HTML tags
        return text[:200] + '...' if len(text) > 200 else text

class PostDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed post view"""
    author = UserSerializer(read_only=True)
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        required=True
    )
    tags = TagSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    building_references = BuildingReferenceSerializer(many=True)
    category_details = CategorySerializer(source='category', read_only=True)  
    comment_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.SerializerMethodField()
    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'content', 'author',
            'category', 'category_details', 'status', 'tags',
            'view_count', 'like_count', 'is_pinned','building_references','comments',
            'created_at', 'last_activity_at', 'comment_count', 'is_liked'
        ]
        read_only_fields = ['slug', 'view_count', 'like_count']
    def get_is_liked(self, obj):
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        return user in obj.likes.all() if user else False



    def get_excerpt(self, obj):
        """Return a plain text excerpt of the post content"""
        text = strip_tags(obj.content)  # Remove HTML tags
        return text[:200] + '...' if len(text) > 200 else text
    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required to create posts")

        # Extract tags and building_references from validated_data
        tags_data = validated_data.pop('tags', [])
        building_references_data = validated_data.pop('building_references', [])

        # Set the author to the current user
        validated_data['author'] = request.user

        # Create the post
        post = Post.objects.create(**validated_data)

        # Add tags
        for tag_name in tags_data:
            tag, _ = Tag.objects.get_or_create(name=tag_name)
            PostTag.objects.create(post=post, tag=tag)

        # Add building references
        for ref_data in building_references_data:
            # ref_data should include 'building_id', 'reference_type', 'context'
            # Make sure 'building_id' exists. If it's just 'building_id', you need to fetch the building object
            building_id = ref_data.pop('building_id')
            building = Building.objects.get(id=building_id)
            BuildingReference.objects.create(post=post, building=building, **ref_data)

        return post

    def update(self, instance, validated_data):
        instance.title = validated_data.get('title', instance.title)
        instance.content = validated_data.get('content', instance.content)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        tags_data = validated_data.pop('tags', [])
        building_references_data = validated_data.pop('building_references', [])
        
        # Update post fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update tags
        instance.tags.clear()
        for tag_data in tags_data:
            tag, _ = Tag.objects.get_or_create(**tag_data)
            instance.tags.add(tag)
        
        # Update building references
        instance.building_references.all().delete()
        for ref_data in building_references_data:
            BuildingReference.objects.create(post=instance, **ref_data)
        
        return instance

class PostDraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostDraft
        fields = ['id', 'title', 'content', 'category', 'saved_at']
        read_only_fields = ['saved_at']