from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import Category, Post, Comment, Tag, PostDraft, PostTag, BuildingReference
from .serializers import (
    CategorySerializer,
    PostListSerializer,
    PostDetailSerializer,
    CommentSerializer,
    TagSerializer,
    PostDraftSerializer
)
from django.db.models import F, ExpressionWrapper, IntegerField
from django.db.models import Count, Max
from .permissions import IsAuthorOrReadOnly, IsModerator
from django_filters import rest_framework as django_filters

# Add a custom filter for PostViewSet
class PostFilter(django_filters.FilterSet):
    category_slug = django_filters.CharFilter(field_name='category__slug')
    tags = django_filters.CharFilter(method='filter_by_tags')
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Post
        fields = ['category_slug', 'status', 'tags']

    def filter_by_category_slug(self, queryset, name, value):
        return queryset.filter(category__slug=value)

    def filter_by_tags(self, queryset, name, value):
        tag_names = value.split(',')
        return queryset.filter(tags__name__in=tag_names).distinct()

class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostDetailSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_class = PostFilter
    search_fields = ['title', 'content', 'author__username']
    ordering_fields = ['created_at', 'last_activity_at', 'view_count', 'like_count']
    # lookup_field = 'slug'

    def get_queryset(self):
        queryset = Post.objects.annotate(
            comment_count=Count('comments'),
            latest_comment_date=Max('comments__created_at')
        )
        # Filter based on status and user
        if self.request.user.is_authenticated:
            queryset = queryset.filter(
                Q(status='published') | Q(author=self.request.user)
            )
        else:
            queryset = queryset.filter(status='published')

        # Apply sorting
        sort_by = self.request.query_params.get('sort', 'newest')
        if sort_by == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort_by == 'popular':
            queryset = queryset.order_by('-like_count', '-created_at')
        elif sort_by == 'discussed':
            queryset = queryset.order_by('-comment_count', '-created_at')

        return queryset.select_related(
            'author', 
            'category'
        ).prefetch_related('tags')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['POST'])
    def toggle_like(self, request, pk=None):
        """Toggle like status for a post"""
        post = self.get_object()
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=401)
        
        liked = post.toggle_like(request.user)
        
        return Response({
            'liked': liked,
            'like_count': post.like_count
        })

    @action(detail=False)
    def trending(self, request):
        """Get trending posts based on engagement"""
        posts = Post.objects.filter(status='published')\
            .annotate(
                comment_count=Count('comments'),  
                engagement_score=ExpressionWrapper(
                    F('like_count') * 2 + F('comment_count') * 3,
                    output_field=IntegerField()
                )
            ).order_by('-engagement_score', '-created_at')[:10]
        
        serializer = PostListSerializer(
            posts, 
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)
    
    @action(detail=True, methods=['POST'])
    def comments(self, request, pk=None):
        post = self.get_object()
        serializer = CommentSerializer(
            data=request.data,
            context={
                'request': request,
                'post': post
            }
        )
        if serializer.is_valid():
            serializer.save(post=post) 
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            # Handle tags
            if 'tags' in request.data:
                instance.tags.clear()
                for tag_name in request.data['tags']:
                    tag, _ = Tag.objects.get_or_create(name=tag_name)
                    instance.tags.add(tag)

            # Handle building references
            if 'building_references' in request.data:
                # Delete existing building references
                BuildingReference.objects.filter(post=instance).delete()
                # Create new building references
                for ref in request.data['building_references']:
                    BuildingReference.objects.create(
                        post=instance,
                        building_id=ref['building_id'],
                        reference_type=ref.get('reference_type', 'mention')
                    )

            self.perform_update(serializer)

            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny] 
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

    def get_queryset(self):
        return self.queryset.annotate(
            active_posts_count=Count(
                'posts',
                filter=Q(
                    posts__status='published',
                    posts__last_activity_at__gte=timezone.now() - timezone.timedelta(days=30)
                )
            ),
            latest_post_date=Max('posts__created_at')
        )

    @action(detail=True)
    def stats(self, request, slug=None):
        category = self.get_object()
        posts = Post.objects.filter(
            category=category,
            status='published'
        )
        
        # Get tags using the correct relationship
        tags_data = PostTag.objects.filter(
            post__category=category,
            post__status='published'
        ).values('tag__id', 'tag__name', 'tag__slug'
        ).annotate(
            usage_count=Count('tag')
        ).order_by('-usage_count')[:10]

        popular_tags = [
            {
                'id': tag['tag__id'],
                'name': tag['tag__name'],
                'slug': tag['tag__slug'],
                'usage_count': tag['usage_count']
            }
            for tag in tags_data
        ]
        
        return Response({
            'total_posts': posts.count(),
            'total_comments': Comment.objects.filter(
                post__in=posts
            ).count(),
            'active_posts': posts.filter(
                last_activity_at__gte=timezone.now() - timezone.timedelta(days=30)
            ).count(),
            'latest_posts': PostListSerializer(
                posts.order_by('-created_at')[:5], 
                many=True
            ).data,
            'popular_tags': popular_tags
        })

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