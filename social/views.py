from django.shortcuts import render, redirect
from django.db.models import Q
from django.utils import timezone
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.views import View
from .models import Post, Comment, UserProfile, Notification, ThreadModel, MessageModel, Image, Tag
from .forms import PostForm, CommentForm, ThreadForm, MessageForm, ShareForm, ExploreForm
from django.views.generic.edit import UpdateView, DeleteView


class PostListView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        
        logged_in_user = request.user
        # The request.user attribute contains the user object associated with the current session. django session???
        
        posts = Post.objects.filter( #This line queries the database to retrieve posts that are relevant to the logged-in user. 
            author__profile__followers__in=[logged_in_user.id]
            # This filter uses Django's double underscore notation to navigate relationships. 
            # This aims to fetch posts authored by users who are followed by the logged-in user.
        )

        form = PostForm()

        share_form = ShareForm()

        context = { 
            # This dictionary defines the context data that will be passed to the template when rendering.
            'post_list': posts, #The variable posts containing the filtered posts.
            'shareform': share_form, # The instance of the share form.
            'form': form, #The instance of the post creation form.
        }
        return render(request, 'social/post_list.html', context) # It's using Django's render function to generate the HTML content that will be sent as the response.

    def post(self, request, *args, **kwargs):
        logged_in_user = request.user
        posts = Post.objects.filter(
            author__profile__followers__in=[logged_in_user.id]
        )
        form = PostForm(request.POST, request.FILES) # form creates an instance of the PostForm class, passing two arguments:
        
        # request.POST: In the context of Django, when a user submits a form via POST (e.g., by submitting a web form), 
        # the data from the form fields is sent in the POST dictionary. The request.POST attribute contains this data.
        
        # request.FILES: In Django, when a form includes a file input field (e.g., for uploading images or documents), 
        # the uploaded files are stored in the request.FILES dictionary.

        files = request.FILES.getlist('image') #collecting all the uploaded files that are stored in image model.
        share_form = ShareForm()

        if form.is_valid():
            new_post = form.save(commit=False) #it creates the model instance in memory but doesn't perform the database insertion yet.
            new_post.author = request.user
            new_post.save()
            # we save the post body first so that we have the access to the id.

            new_post.create_tags() #if there is hashtags in my post then treat them differenly.

            for f in files:
                img = Image(image=f)
                img.save()
                new_post.image.add(img)
                #This line adds the Image instance (img) to the image many-to-many relationship of the new_post instance. 
                # In Django, when you have a many-to-many relationship field between two models, 
                # you can use the add() method to associate instances from one model with instances from another model.

            new_post.save() #here it saves the post with multiple images.


        context = {
            'post_list': posts,
            'shareform': share_form,
            'form': form,
        }

        # now create some sort of slider for multiple images
        return render(request, 'social/post_list.html', context)
    
    
# ***************************************************************************************************************** #


class PostDetailView(LoginRequiredMixin, View):
    def get(self, request, pk, *args, **kwargs):
        post = Post.objects.get(pk=pk)
        form = CommentForm()

        comments = Comment.objects.filter(post=post)

        context = {
            'post': post,
            'form': form,
            'comments': comments,
        }

        return render(request, 'social/post_detail.html', context)
    def post(self, request, pk, *args, **kwargs):
        post = Post.objects.get(pk=pk) # fetches that particular post by using primary key.

        form = CommentForm(request.POST)

        if form.is_valid():
            new_comment = form.save(commit=False)
            new_comment.author = request.user
            new_comment.post = post
            new_comment.save()

            new_comment.create_tags() #if there is any hashtags in my post then treat them differenly.

        comments = Comment.objects.filter(post=post)
        #  This line retrieves all comments associated with the post and stores them in the comments variable.

        notification = Notification.objects.create(notification_type=2, from_user=request.user, to_user=post.author, post=post)

        context = {
            'post': post,
            'form': form,
            'comments': comments,
        }

        return render(request, 'social/post_detail.html', context)
    
    
# ***************************************************************************************************************** #


class CommentReplyView(LoginRequiredMixin, View):
    def post(self, request, post_pk, pk, *args, **kwargs):
        post = Post.objects.get(pk=post_pk)
        parent_comment = Comment.objects.get(pk=pk)
        form = CommentForm(request.POST)

        if form.is_valid():
            new_comment = form.save(commit=False)
            new_comment.author = request.user
            new_comment.post = post
            new_comment.parent = parent_comment
            new_comment.save()

        notification = Notification.objects.create(notification_type=2, from_user=request.user, to_user=parent_comment.author, comment=new_comment)

        return redirect('post-detail', pk=post_pk)
    
# ***************************************************************************************************************** #

# start from here.
class PostEditView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    fields = ['body']
    # The model attribute is set to Post, which indicates that this view will work with the Post model. 
    # The fields attribute is a list containing the names of the fields,
    # that can be edited in the form associated with this view. 

    template_name = 'social/post_edit.html' #indicating the template that will be used to render this view.

    def get_success_url(self): #This method determines the URL to redirect to after successfully editing a post.
        pk = self.kwargs['pk'] #basically, it is used to extract the arguments from the url That i have been passed in urls.py, by using sel.kwargs dictionary.
        return reverse_lazy('post-detail', kwargs={'pk': pk})
        # reverse_lazy is a function used to generate URLs for views based on their URL patterns. 
        # It's particularly useful in class-based views where you need to dynamically generate URLs, 
        # such as when you want to redirect users after a successful action.

    def test_func(self): #This method is used to determine whether the logged-in user is authorized to edit the post.
        post = self.get_object()
        return self.request.user == post.author

class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    template_name = 'social/post_delete.html'
    success_url = reverse_lazy('post-list')

    # here we are not using get_success_url() method bcoz here we are not passing any pk so by using success_url, we set the urls after completion the task, when we should have to render.

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author
    

# ***************************************************************************************************************** #


class CommentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Comment
    template_name = 'social/comment_delete.html'

    def get_success_url(self):
        pk = self.kwargs['post_pk']
        return reverse_lazy('post-detail', kwargs={'pk': pk})

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author
    
# ***************************************************************************************************************** #

class ProfileView(View):
    def get(self, request, pk, *args, **kwargs):
        profile = UserProfile.objects.get(pk=pk) # gets the profile which associated with the given primary key from userProfile model.
        user = profile.user # retreive the user.
        posts = Post.objects.filter(author=user) # retreive all the post of that user.

        followers = profile.followers.all() # retreive all the followers of that particular profile has.


        # Now, we check if the reqest user isfollowing the profile.user or not if not then render the follow button otherwise show unfollow button.

        if len(followers) == 0:             
            is_following = False

        for follower in followers:
            if follower == request.user:
                is_following = True
                break
            else:
                is_following = False

        number_of_followers = len(followers)



        context = {
            'user': user,
            'profile': profile,
            'posts': posts,
            'number_of_followers': number_of_followers,
            'is_following': is_following,
        }
        # pasing context dictionary to the template when rendering.

        return render(request, 'social/profile.html', context)
    


# ***************************************************************************************************************** #


class ProfileEditView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = UserProfile
    fields = ['name', 'bio', 'birth_date', 'location', 'picture']
    template_name = 'social/profile_edit.html'

    def get_success_url(self):
        pk = self.kwargs['pk']
        return reverse_lazy('profile', kwargs={'pk': pk})

    def test_func(self):
        profile = self.get_object()
        return self.request.user == profile.user
    
    
# ***************************************************************************************************************** #


class AddFollower(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        profile = UserProfile.objects.get(pk=pk)
        profile.followers.add(request.user) # adding the requested user to the following list of the profile.user

        notification = Notification.objects.create(notification_type=3, from_user=request.user, to_user=profile.user)

        return redirect('profile', pk=profile.pk)
    

# ***************************************************************************************************************** #


class RemoveFollower(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        profile = UserProfile.objects.get(pk=pk)
        profile.followers.remove(request.user) # if the request.user exists in followers list of profile than remove.

        return redirect('profile', pk=profile.pk)
    


# ***************************************************************************************************************** #


class AddLike(LoginRequiredMixin, View):
    # for like and dislike the user should have to be logged in.
    def post(self, request, pk, *args, **kwargs):
        post = Post.objects.get(pk=pk) # fetches the post with given pk.

        is_dislike = False

        for dislike in post.dislikes.all():
            if dislike == request.user:
                is_dislike = True
                break

        if is_dislike:
            post.dislikes.remove(request.user)

        is_like = False

        for like in post.likes.all():
            if like == request.user:
                is_like = True
                break

        if not is_like:
            post.likes.add(request.user)
            notification = Notification.objects.create(notification_type=1, from_user=request.user, to_user=post.author, post=post)

        if is_like:
            post.likes.remove(request.user)


        
# next used to perform a redirect to a specified URL after a certain action, such as submitting a form.
# If the 'next' key is present in the request.POST dictionary and has a value, the get() method returns that value.
# If the 'next' key is not present in the dictionary, the get() method returns '/'.

        next = request.POST.get('next', '/')
        # request.POST: In Django, when a user submits a form using the POST method, 
        # the form data is sent to the server as part of the request's POST dictionary. 
        # This dictionary contains key-value pairs where the keys are the names of form fields, 
        # and the values are the data entered by the user.
        return HttpResponseRedirect(next)
    



# ***************************************************************************************************************** #


class AddDislike(LoginRequiredMixin, View):
    # for like and dislike the user should have to be logged in.
    def post(self, request, pk, *args, **kwargs):
        post = Post.objects.get(pk=pk)

        is_like = False

        for like in post.likes.all():
            if like == request.user:
                is_like = True
                break

        if is_like:
            post.likes.remove(request.user)

        is_dislike = False

        for dislike in post.dislikes.all():
            if dislike == request.user:
                is_dislike = True
                break

        if not is_dislike:
            post.dislikes.add(request.user)

        if is_dislike:
            post.dislikes.remove(request.user)

        next = request.POST.get('next', '/') #by this we can return to our previous view or template
        return HttpResponseRedirect(next)
    

# ***************************************************************************************************************** #


class AddCommentLike(LoginRequiredMixin, View):
    # for like and dislike the user should have to be logged in.
    def post(self, request, pk, *args, **kwargs):
        comment = Comment.objects.get(pk=pk)

        is_dislike = False

        for dislike in comment.dislikes.all():
            if dislike == request.user:
                is_dislike = True
                break

        if is_dislike:
            comment.dislikes.remove(request.user)

        is_like = False

        for like in comment.likes.all():
            if like == request.user:
                is_like = True
                break

        if not is_like:
            comment.likes.add(request.user)
            notification = Notification.objects.create(notification_type=1, from_user=request.user, to_user=comment.author, comment=comment)

        if is_like:
            comment.likes.remove(request.user)

        next = request.POST.get('next', '/')
        return HttpResponseRedirect(next)
    


# ***************************************************************************************************************** #


class AddCommentDislike(LoginRequiredMixin, View):
    # for like and dislike the user should have to be logged in.
    def post(self, request, pk, *args, **kwargs):
        comment = Comment.objects.get(pk=pk)

        is_like = False

        for like in comment.likes.all():
            if like == request.user:
                is_like = True
                break

        if is_like:
            comment.likes.remove(request.user)

        is_dislike = False

        for dislike in comment.dislikes.all():
            if dislike == request.user:
                is_dislike = True
                break

        if not is_dislike:
            comment.dislikes.add(request.user)

        if is_dislike:
            comment.dislikes.remove(request.user)

        next = request.POST.get('next', '/')
        return HttpResponseRedirect(next)
    


# ***************************************************************************************************************** #


class SharedPostView(View):
    def post(self, request, pk, *args, **kwargs):
       original_post = Post.objects.get(pk=pk) 
       # This line retrieves the original post that the user wants to share from the database. 
       # The pk parameter is used to identify the specific post.
       form = ShareForm(request.POST)
    #    This form is used to gather additional information about the shared post, 
    # such as an optional comment or description.

       if form.is_valid():
            new_post = Post(
                shared_body=self.request.POST.get('body'),
                body=original_post.body,
                author=original_post.author,
                created_on=original_post.created_on,
                shared_user=request.user,
                shared_on=timezone.now(),
            )
            new_post.save()

            for img in original_post.image.all():
                new_post.image.add(img)

            new_post.save()

       return redirect('post-list')


# ***************************************************************************************************************** #


class UserSearch(View):
    def get(self, request, *args, **kwargs):
        query = self.request.GET.get('query')
        profile_list = UserProfile.objects.filter(
            Q(user__username__icontains=query)
        )

        context = {
            'profile_list': profile_list,
        }

        return render(request, 'social/search.html', context)
    


# ***************************************************************************************************************** #


class ListFollowers(View):
    def get(self, request, pk, *args, **kwargs):
        profile = UserProfile.objects.get(pk=pk)
        followers = profile.followers.all()

        context = {
            'profile': profile,
            'followers': followers,
        }

        return render(request, 'social/followers_list.html', context)

class PostNotification(View):
    def get(self, request, notification_pk, post_pk, *args, **kwargs):
        notification = Notification.objects.get(pk=notification_pk)
        post = Post.objects.get(pk=post_pk)

        notification.user_has_seen = True
        notification.save()

        return redirect('post-detail', pk=post_pk)

class FollowNotification(View):
    def get(self, request, notification_pk, profile_pk, *args, **kwargs):
        notification = Notification.objects.get(pk=notification_pk)
        profile = UserProfile.objects.get(pk=profile_pk)

        notification.user_has_seen = True
        notification.save()

        return redirect('profile', pk=profile_pk)

class ThreadNotification(View):
    def get(self, request, notification_pk, object_pk, *args, **kwargs):
        notification = Notification.objects.get(pk=notification_pk)
        thread = ThreadModel.objects.get(pk=object_pk)

        notification.user_has_seen = True
        notification.save()

        return redirect('thread', pk=object_pk)

class RemoveNotification(View):
    def delete(self, request, notification_pk, *args, **kwargs):
        notification = Notification.objects.get(pk=notification_pk)

        notification.user_has_seen = True
        notification.save()

        return HttpResponse('Success', content_type='text/plain')

class ListThreads(View):
    def get(self, request, *args, **kwargs):
        threads = ThreadModel.objects.filter(Q(user=request.user) | Q(receiver=request.user))

        context = {
            'threads': threads
        }

        return render(request, 'social/inbox.html', context)

class CreateThread(View):
    def get(self, request, *args, **kwargs):
        form = ThreadForm()

        context = {
            'form': form
        }

        return render(request, 'social/create_thread.html', context)

    def post(self, request, *args, **kwargs):
        form = ThreadForm(request.POST)

        username = request.POST.get('username')

        try:
            receiver = User.objects.get(username=username)
            if ThreadModel.objects.filter(user=request.user, receiver=receiver).exists():
                thread = ThreadModel.objects.filter(user=request.user, receiver=receiver)[0]
                return redirect('thread', pk=thread.pk)
            elif ThreadModel.objects.filter(user=receiver, receiver=request.user).exists():
                thread = ThreadModel.objects.filter(user=receiver, receiver=request.user)[0]
                return redirect('thread', pk=thread.pk)

            if form.is_valid():
                thread = ThreadModel(
                    user=request.user,
                    receiver=receiver
                )
                thread.save()

                return redirect('thread', pk=thread.pk)
        except:
            messages.error(request, 'Invalid username')
            return redirect('create-thread')

class ThreadView(View):
    def get(self, request, pk, *args, **kwargs):
        form = MessageForm()
        thread = ThreadModel.objects.get(pk=pk)
        message_list = MessageModel.objects.filter(thread__pk__contains=pk)
        context = {
            'thread': thread,
            'form': form,
            'message_list': message_list
        }

        return render(request, 'social/thread.html', context)

class CreateMessage(View):
    def post(self, request, pk, *args, **kwargs):
        form = MessageForm(request.POST, request.FILES)
        thread = ThreadModel.objects.get(pk=pk)
        if thread.receiver == request.user:
            receiver = thread.user
        else:
            receiver = thread.receiver

        if form.is_valid():
            message = form.save(commit=False)
            message.thread = thread
            message.sender_user = request.user
            message.receiver_user = receiver
            message.save()

        notification = Notification.objects.create(
            notification_type=4,
            from_user=request.user,
            to_user=receiver,
            thread=thread
        )
        return redirect('thread', pk=pk)


class Explore(View):
    def get(self, request, *args, **kwargs):
        explore_form = ExploreForm()
        query = self.request.GET.get('query')
        tag = Tag.objects.filter(name = query).first()

        if tag:
            posts = Post.objects.filter(tags__in = [tag])
        else: 
            posts = Post.objects.all()
        
        context = {
            'tag' : tag, 
            'posts' : posts,
            'explore_form': explore_form
        }

        return render(request, 'social/explore.html', context)
    
    def post(self, request, *args, **kwargs):
        explore_form = ExploreForm(request.POST)
        if explore_form.is_valid():
            query = explore_form.cleaned_data['query']
            tag = Tag.objects.filter(name = query).first()

            posts = None
            if tag:
                posts = Post.objects.filter(tags__in=[tag])

            if posts:
                context = {
                    'tag':tag,
                    'posts' : posts,
                }
            else:
                context = {
                    'tag' : tag,
                }
            return HttpResponseRedirect(f'/social/explore?query={query}')
        return HttpResponseRedirect('/social/explore')

