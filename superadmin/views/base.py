from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from superadmin.mixins import SuperuserRequiredMixin


class BaseSuperadminListView(SuperuserRequiredMixin, ListView):
    paginate_by = 10
    search_fields = ()

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q and self.search_fields:
            from django.db.models import Q
            condition = Q()
            for field in self.search_fields:
                condition |= Q(**{f"{field}__icontains": q})
            qs = qs.filter(condition)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "")
        return context


class BaseSuperadminDetailView(SuperuserRequiredMixin, DetailView):
    pass


class BaseSuperadminCreateView(SuperuserRequiredMixin, CreateView):
    success_message = "Record created successfully."

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, self.success_message)
        return response


class BaseSuperadminUpdateView(SuperuserRequiredMixin, UpdateView):
    success_message = "Record updated successfully."

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, self.success_message)
        return response


class BaseSuperadminDeleteView(SuperuserRequiredMixin, DeleteView):
    success_message = "Record deleted successfully."
    template_name = "superadmin/confirm_delete.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("cancel_url", self.success_url)
        return context

    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super().form_valid(form)
