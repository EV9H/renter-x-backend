from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import Category, Post, Comment, Tag, PostDraft
from .serializers import (
    CategorySerializer,
    PostListSerializer,
    PostDetailSerializer,
    CommentSerializer,
    TagSerializer,
    PostDraftSerializer
)

from django.db.models import Count, Max
from .permissions import IsAuthorOrReadOnly, IsModerator

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny] 
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

    def get_queryset(self):
        return self.queryset.annotate(
            annotated_post_count=Count('posts')
        )

    @action(detail=True)
    def stats(self, request, slug=None):
        category = self.get_object()
        posts = Post.objects.filter(category=category)
        
        return Response({
            'total_posts': posts.count(),
            'total_comments': Comment.objects.filter(post__category=category).count(),
            'active_posts': posts.filter(
                last_activity_at__gte=timezone.now() - timezone.timedelta(days=30)
            ).count(),
            'latest_posts': PostListSerializer(
                posts.order_by('-created_at')[:5], 
                many=True
            ).data
        })

class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostListSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'status', 'tags']
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'last_activity_at', 'view_count', 'like_count']
    lookup_field = 'slug'
    queryset = Post.objects.all()  # Add this line

    def get_queryset(self):
        queryset = Post.objects.annotate(
            comment_count=Count('comments'),
            latest_comment_date=Max('comments__created_at')
        )
        
        # Filter based on status
        if self.action == 'list':
            queryset = queryset.filter(Q(status='published') | Q(author=self.request.user))
        
        return queryset.select_related('author', 'category').prefetch_related('tags')
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PostDetailSerializer
        return PostListSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.save()
        # Update last_activity_at when post is updated
        instance.last_activity_at = timezone.now()
        instance.save()

    @action(detail=True, methods=['post'])
    def like(self, request, slug=None):
        post = self.get_object()
        post.like_count += 1
        post.save()
        return Response({'status': 'success', 'like_count': post.like_count})

    @action(detail=True, methods=['post'])
    def unlike(self, request, slug=None):
        post = self.get_object()
        if post.like_count > 0:
            post.like_count -= 1
            post.save()
        return Response({'status': 'success', 'like_count': post.like_count})

    @action(detail=True, methods=['post'])
    def view(self, request, slug=None):
        post = self.get_object()
        post.view_count += 1
        post.save()
        return Response({'status': 'success', 'view_count': post.view_count})

class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['post', 'parent']
    ordering_fields = ['created_at', 'like_count']

    def get_queryset(self):
        return Comment.objects.filter(
            post_id=self.kwargs.get('post_pk')
        ).select_related('author').prefetch_related('replies')

    def perform_create(self, serializer):
        post = get_object_or_404(Post, pk=self.kwargs.get('post_pk'))
        serializer.save(
            author=self.request.user,
            post=post
        )
        # Update post's last_activity_at
        post.last_activity_at = timezone.now()
        post.save()

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None, post_pk=None):
        comment = self.get_object()
        comment.like_count += 1
        comment.save()
        return Response({'status': 'success', 'like_count': comment.like_count})

class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

    @action(detail=True)
    def posts(self, request, slug=None):
        tag = self.get_object()
        posts = Post.objects.filter(
            tags=tag,
            status='published'
        ).order_by('-created_at')
        serializer = PostListSerializer(posts, many=True)
        return Response(serializer.data)

class PostDraftViewSet(viewsets.ModelViewSet):
    serializer_class = PostDraftSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PostDraft.objects.filter(author=self.request.user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        draft = self.get_object()
        # Create a new post from the draft
        post = Post.objects.create(
            title=draft.title,
            content=draft.content,
            author=request.user,
            category=draft.category,
            status='published'
        )
        # Delete the draft
        draft.delete()
        return Response(PostDetailSerializer(post).data)