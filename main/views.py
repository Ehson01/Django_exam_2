from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode, url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.db.models import Avg, Count

from .models import Category, Company, Job, Application


# admin
def is_admin(user):
    return user.is_staff or user.is_superuser


def can_manage_job(user, job):
    return user.is_authenticated and (
        user.id == job.created_by_id or is_admin(user)
    )


def deny(request, text, page, *args):
    return redirect(page, *args)



def home_page(request):
    return render(request, 'home_page.html', {
        'latest_jobs': Job.objects.all()[:6],
        'jobs_total': Job.objects.count(),
        'companies_total': Company.objects.count(),
        'applications_total': Application.objects.count(),
    })


def stats(request):
    return render(request, 'stats.html', {
        'jobs_total': Job.objects.count(),
        'average_salary': Job.objects.aggregate(avg=Avg('salary'))['avg'],
        'applications_total': Application.objects.count(),
        'companies': Company.objects.annotate(jobs_count=Count('jobs')),
    })


# CRUd

# category
def category_list(request):
    return render(request, 'category_list.html', {
        'categories': Category.objects.annotate(jobs_count=Count('jobs'))
    })


@login_required
def category_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()

        if name:
            Category.objects.create(name=name)
            return redirect('category_list')

    return render(request, 'category_create.html')


@login_required
def category_update(request, pk):
    category = get_object_or_404(Category, pk=pk)

    if not is_admin(request.user):
        return redirect('category_list')

    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.save()
        return redirect('category_list')

    return render(request, 'category_update.html', {
        'category': category
    })


@login_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)

    if not is_admin(request.user):
        return redirect('category_list')

    if request.method == 'POST':
        category.delete()
        return redirect('category_list')

    return render(request, 'confirm_delete.html', {
        'title': 'Delete category?',
        'text': f'The category "{category.name}" and its jobs will be deleted.',
        'back_url': 'category_list',
    })


# ____________________________________________________company


def company_list(request):
    return render(request, 'company_list.html', {
        'companies': Company.objects.annotate(jobs_count=Count('jobs'))
    })


def company_detail(request, pk):
    company = get_object_or_404(Company, pk=pk)

    return render(request, 'company_detail.html', {
        'company': company,
        'jobs': company.jobs.all(),
    })


@login_required
def company_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()

        if name:
            company = Company.objects.create(
                name=name,
                description=request.POST.get('description', ''),
                website=request.POST.get('website', ''),
            )
            return redirect('company_detail', pk=company.pk)

    return render(request, 'company_create.html')


@login_required
def company_update(request, pk):
    company = get_object_or_404(Company, pk=pk)

    if not is_admin(request.user):
        return redirect('company_detail', pk=company.pk)

    if request.method == 'POST':
        company.name = request.POST.get('name')
        company.description = request.POST.get('description')
        company.website = request.POST.get('website')
        company.save()

        return redirect('company_detail', pk=company.pk)

    return render(request, 'company_update.html', {
        'company': company
    })


@login_required
def company_delete(request, pk):
    company = get_object_or_404(Company, pk=pk)

    if not is_admin(request.user):
        return redirect('company_detail', pk=company.pk)

    if request.method == 'POST':
        company.delete()
        return redirect('company_list')

    return render(request, 'confirm_delete.html', {
        'title': 'Delete company?',
        'text': f'The company "{company.name}" and its jobs will be deleted.',
        'back_url': 'company_list',
    })


# ____________________________job
def job_list(request):
    jobs = Job.objects.all()

    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    company_id = request.GET.get('company', '')
    min_salary = request.GET.get('min_salary', '')

    if query:
        jobs = jobs.filter(title__icontains=query)

    if category_id.isdigit():
        jobs = jobs.filter(category_id=category_id)

    if company_id.isdigit():
        jobs = jobs.filter(company_id=company_id)

    if min_salary.isdigit():
        jobs = jobs.filter(salary__gte=min_salary)

    jobs = jobs.exclude(salary__lte=0)

    return render(request, 'job_list.html', {
        'jobs': jobs,
        'categories': Category.objects.all(),
        'companies': Company.objects.all(),
        'query': query,
        'category_id': category_id,
        'company_id': company_id,
        'min_salary': min_salary,
    })


def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk)

    return render(request, 'job_detail.html', {
        'job': job,
        'applications': job.applications.all(),
        'can_manage': can_manage_job(request.user, job),
    })


@login_required
def job_create(request):
    if request.method == 'POST':
        job = Job.objects.create(
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            salary=request.POST.get('salary'),
            location=request.POST.get('location'),
            employment_type=request.POST.get('employment_type'),
            company=get_object_or_404(
                Company, pk=request.POST.get('company')
            ),
            category=get_object_or_404(
                Category, pk=request.POST.get('category')
            ),
            created_by=request.user,
        )

        return redirect('job_detail', pk=job.pk)

    return render(request, 'job_create.html', {
        'companies': Company.objects.all(),
        'categories': Category.objects.all(),
        'employment_choices': Job.EMPLOYMENT_CHOICES,
    })


@login_required
def job_update(request, pk):
    job = get_object_or_404(Job, pk=pk)

    if not can_manage_job(request.user, job):
        return redirect('job_detail', pk=job.pk)

    if request.method == 'POST':
        job.title = request.POST.get('title')
        job.description = request.POST.get('description')
        job.salary = request.POST.get('salary')
        job.location = request.POST.get('location')
        job.employment_type = request.POST.get('employment_type')

        job.company = get_object_or_404(
            Company, pk=request.POST.get('company')
        )

        job.category = get_object_or_404(
            Category, pk=request.POST.get('category')
        )

        job.save()

        return redirect('job_detail', pk=job.pk)

    return render(request, 'job_update.html', {
        'job': job,
        'companies': Company.objects.all(),
        'categories': Category.objects.all(),
        'employment_choices': Job.EMPLOYMENT_CHOICES,
    })


@login_required
def job_delete(request, pk):
    job = get_object_or_404(Job, pk=pk)

    if not can_manage_job(request.user, job):
        return redirect('job_detail', pk=job.pk)

    if request.method == 'POST':
        job.delete()
        return redirect('job_list')

    return render(request, 'job_delete.html', {
        'job': job
    })


# _____________application

@login_required
def application_create(request, pk):
    job = get_object_or_404(Job, pk=pk)

    if job.created_by_id == request.user.id:
        return redirect('job_detail', pk=job.pk)

    if Application.objects.filter(job=job, user=request.user).exists():
        return redirect('job_detail', pk=job.pk)

    if request.method == 'POST':
        Application.objects.create(
            job=job,
            user=request.user,
            cover_letter=request.POST.get('cover_letter', '')
        )

        return redirect('job_detail', pk=job.pk)

    return render(request, 'application_create.html', {
        'job': job
    })


@login_required
def application_update(request, pk):
    application = get_object_or_404(Application, pk=pk)

    is_author = application.user == request.user
    is_manager = can_manage_job(request.user, application.job)

    if not is_author and not is_manager:
        return redirect('job_detail', pk=application.job_id)

    if request.method == 'POST':
        if is_author:
            application.cover_letter = request.POST.get('cover_letter', '')

        if is_manager:
            application.status = request.POST.get(
                'status', application.status
            )

        application.save()

        return redirect('job_detail', pk=application.job_id)

    return render(request, 'application_update.html', {
        'application': application,
        'is_author_of_application': is_author,
        'is_manager': is_manager,
        'status_choices': Application.STATUS_CHOICES,
    })


@login_required
def application_delete(request, pk):
    application = get_object_or_404(Application, pk=pk)

    if application.user != request.user and not can_manage_job(
        request.user, application.job
    ):
        return redirect('job_detail', pk=application.job_id)

    if request.method == 'POST':
        job_id = application.job_id
        application.delete()
        return redirect('job_detail', pk=job_id)

    return render(request, 'confirm_delete.html', {
        'title': 'Delete application?',
        'text': f'Your application for "{application.job.title}" will be deleted.',
        'back_url': 'profile',
    })


# ________________email

def send_link_email(request, user, view_name, subject, text):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    link = request.build_absolute_uri(
        reverse(view_name, args=[uid, token])
    )

    send_mail(
        subject,
        f'Hello, {user.username}!\n\n{text}\n{link}\n',
        None,
        [user.email]
    )


def get_user_from_uid(uid):
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        return User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None


def check_new_password(user, password1, password2):
    errors = []

    if password1 != password2:
        errors.append('Passwords do not match.')
        return errors

    try:
        validate_password(password1, user=user)
    except ValidationError as error:
        errors.extend(error.messages)

    return errors


def register(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        errors = check_new_password(
            User(username=username, email=email),
            password1,
            password2
        )

        if not username or not email:
            errors.append('Enter your username and email.')

        if User.objects.filter(username__iexact=username).exists():
            errors.append('This username is already taken.')

        if User.objects.filter(email__iexact=email).exists():
            errors.append('This email is already registered.')

        if errors:
            return render(request, 'register.html', {
                'errors': errors
            })

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            is_active=False
        )

        send_link_email(
            request,
            user,
            'activate',
            'Job Portal: confirm your email',
            'To activate your account, open this link:'
        )

        return redirect('login')

    return render(request, 'register.html')


def activate(request, uidb64, token):
    user = get_user_from_uid(uidb64)

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()

    return redirect('login')



def login_view(request):
    next_url = request.POST.get('next') or request.GET.get('next', '')
    errors = []

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)

            if url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()}
            ):
                return redirect(next_url)

            return redirect('home')

        errors.append(
            'Invalid username or password, or your account is not activated.'
        )

    return render(request, 'login.html', {
        'next': next_url,
        'errors': errors
    })


@require_POST
def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def profile(request):
    return render(request, 'profile.html', {
        'my_jobs': request.user.jobs.all(),
        'my_applications': request.user.applications.all(),
    })



@login_required
def password_change(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password', '')
        password1 = request.POST.get('new_password1', '')
        password2 = request.POST.get('new_password2', '')

        errors = check_new_password(
            request.user,
            password1,
            password2
        )

        if not request.user.check_password(old_password):
            errors.append('Your old password is incorrect.')

        if errors:
            return render(request, 'password_change.html', {
                'errors': errors
            })

        request.user.set_password(password1)
        request.user.save()

        update_session_auth_hash(request, request.user)

        return redirect('profile')

    return render(request, 'password_change.html')



def password_reset(request):
    if request.method == 'POST':
        email = request.POST.get('email', '')

        users = User.objects.filter(
            email__iexact=email,
            is_active=True
        )

        for user in users:
            send_link_email(
                request,
                user,
                'password_reset_confirm',
                'Job Portal: password reset',
                'To set a new password, open this link:'
            )

        return redirect('login')

    return render(request, 'password_reset.html')


def password_reset_confirm(request, uidb64, token):
    user = get_user_from_uid(uidb64)

    if user is None or not default_token_generator.check_token(user, token):
        return redirect('password_reset')

    if request.method == 'POST':
        password1 = request.POST.get('new_password1', '')
        password2 = request.POST.get('new_password2', '')

        errors = check_new_password(user, password1, password2)

        if errors:
            return render(request, 'password_reset_confirm.html', {
                'errors': errors
            })

        user.set_password(password1)
        user.save()

        return redirect('login')

    return render(request, 'password_reset_confirm.html')