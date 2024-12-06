from rest_framework import serializers
from .models import Category, Post, Comment, Tag, BuildingReference, PostDraft
from buildings.serializers import BuildingSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        read_only_fields = ['email']

class CategorySerializer(serializers.ModelSerializer):
    post_count = serializers.IntegerField(read_only=True, source='annotated_post_count')
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'parent', 'post_count', 
                 'created_at', 'updated_at']
        read_only_fields = ['slug', 'post_count']

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
                 'created_at', 'updated_at', 'replies']
        read_only_fields = ['author', 'like_count']

    def get_replies(self, obj):
        if not hasattr(obj, 'replies'):
            return []
        serializer = CommentSerializer(obj.replies.all(), many=True)
        return serializer.data

class PostListSerializer(serializers.ModelSerializer):
    """Serializer for listing posts with minimal information"""
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    comment_count = serializers.IntegerField(read_only=True)
    excerpt = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ['id', 'title', 'slug', 'author', 'category', 'tags', 
                 'status', 'view_count', 'like_count', 'is_pinned',
                 'created_at', 'last_activity_at', 'comment_count', 'excerpt']
        read_only_fields = ['slug', 'view_count', 'like_count']

    def get_excerpt(self, obj):
        """Return a short excerpt of the post content"""
        return obj.content[:200] + '...' if len(obj.content) > 200 else obj.content

class PostDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed post view"""
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True)
    comments = CommentSerializer(many=True, read_only=True)
    building_references = BuildingReferenceSerializer(many=True)
    
    class Meta:
        model = Post
        fields = ['id', 'title', 'slug', 'content', 'author', 'category', 
                 'tags', 'status', 'view_count', 'like_count', 'is_pinned',
                 'created_at', 'updated_at', 'last_activity_at', 
                 'comments', 'building_references']
        read_only_fields = ['slug', 'view_count', 'like_count']

    def create(self, validated_data):
        tags_data = validated_data.pop('tags', [])
        building_references_data = validated_data.pop('building_references', [])
        
        post = Post.objects.create(**validated_data)
        
        # Handle tags
        for tag_data in tags_data:
            tag, _ = Tag.objects.get_or_create(**tag_data)
            post.tags.add(tag)
        
        # Handle building references
        for ref_data in building_references_data:
            BuildingReference.objects.create(post=post, **ref_data)
        
        return post

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