import logging

from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from startupscan_api.models import IdeaPitchSubmission, IdeaPublicFeedback
from startupscan_api.roles import (
    ROLE_ADMIN,
    ROLE_ANALISTA,
    ROLE_EMPREENDEDOR,
    ROLE_PUBLICO,
    get_user_role,
)
from startupscan_api.services.pitch_builder import (
    PITCH_DESIGN_MODE_AUTO,
    export_pitch_pdf,
    generate_pitch_from_idea,
    get_pitch_design_mode_choices,
    get_pitch_design_template_choices,
)
from .helpers import _resolve_pitch_design_selection
from .mixins import RoleRequiredMixin

import os
from django.conf import settings

logger = logging.getLogger(__name__)


class IdeaPitchBuilderView(RoleRequiredMixin, View):
    allowed_roles = {ROLE_EMPREENDEDOR, ROLE_ANALISTA, ROLE_ADMIN}

    required_fields = {
        "startup_name": "Nome da startup",
        "problem": "Problema",
        "solution": "Solução",
        "target_customer": "Cliente-alvo",
        "business_model": "Modelo de negócio",
    }

    @staticmethod
    def _collect_form_data(request):
        form_data = {
            "startup_name": request.POST.get("startup_name", "").strip(),
            "one_liner": request.POST.get("one_liner", "").strip(),
            "problem": request.POST.get("problem", "").strip(),
            "solution": request.POST.get("solution", "").strip(),
            "target_customer": request.POST.get("target_customer", "").strip(),
            "market_size": request.POST.get("market_size", "").strip(),
            "business_model": request.POST.get("business_model", "").strip(),
            "competitive_advantage": request.POST.get("competitive_advantage", "").strip(),
            "traction": request.POST.get("traction", "").strip(),
            "team": request.POST.get("team", "").strip(),
            "funding_goal": request.POST.get("funding_goal", "").strip(),
            "use_of_funds": request.POST.get("use_of_funds", "").strip(),
            "call_to_action": request.POST.get("call_to_action", "").strip(),
            "model_source": request.POST.get("model_source", "local").strip().lower(),
        }
        if form_data["model_source"] not in {"local", "gpt"}:
            form_data["model_source"] = "local"
        return form_data

    def _validate(self, form_data):
        errors = {}
        for field, label in self.required_fields.items():
            if not form_data.get(field):
                errors[field] = f"{label} é obrigatório."
        return errors

    def get(self, request):
        return render(request, "analyzer/idea_pitch_form.html", {
            "form_data": {"model_source": "local"},
            "errors": {},
        })

    def post(self, request):
        form_data = self._collect_form_data(request)
        errors = self._validate(form_data)

        if errors:
            messages.error(request, "Preencha os campos obrigatórios para guardar a ideia.")
            return render(request, "analyzer/idea_pitch_form.html", {"form_data": form_data, "errors": errors})

        try:
            submission = IdeaPitchSubmission.objects.create(
                user=request.user if request.user.is_authenticated else None,
                **{k: v for k, v in form_data.items() if k != "model_source"},
                model_source=form_data["model_source"],
            )
            messages.success(request, "Informações guardadas com sucesso. Revise os dados e clique em 'Gerar Pitch Completo'.")
            return redirect("idea_pitch_detail", submission_id=submission.id)
        except Exception as exc:
            logger.error("Falha ao guardar submissão de ideia: %s", str(exc), exc_info=True)
            messages.error(request, "Não foi possível guardar a ideia. Tente novamente.")
            return render(request, "analyzer/idea_pitch_form.html", {"form_data": form_data, "errors": {}})


class IdeaPitchDetailView(RoleRequiredMixin, View):
    allowed_roles = {ROLE_EMPREENDEDOR, ROLE_ANALISTA, ROLE_ADMIN}

    @staticmethod
    def _can_access(request, submission):
        if get_user_role(request.user) == ROLE_ADMIN:
            return True
        if submission.user_id and request.user.is_authenticated:
            return submission.user_id == request.user.id
        if submission.user_id and not request.user.is_authenticated:
            return False
        return True

    @staticmethod
    def _to_payload(submission):
        return {
            "startup_name": submission.startup_name,
            "one_liner": submission.one_liner,
            "problem": submission.problem,
            "solution": submission.solution,
            "target_customer": submission.target_customer,
            "market_size": submission.market_size,
            "business_model": submission.business_model,
            "competitive_advantage": submission.competitive_advantage,
            "traction": submission.traction,
            "team": submission.team,
            "funding_goal": submission.funding_goal,
            "use_of_funds": submission.use_of_funds,
            "call_to_action": submission.call_to_action,
        }

    def get(self, request, submission_id):
        submission = get_object_or_404(IdeaPitchSubmission, id=submission_id)
        if not self._can_access(request, submission):
            return redirect("dashboard")

        design_template_choices = get_pitch_design_template_choices()
        selected_design_mode, selected_design_template = _resolve_pitch_design_selection(
            request,
            default_mode=PITCH_DESIGN_MODE_AUTO,
            default_template=(design_template_choices[0][0] if design_template_choices else "orbit"),
        )
        return render(request, "analyzer/idea_pitch_detail.html", {
            "submission": submission,
            "generated_pitch": submission.generated_pitch if submission.status == "generated" else {},
            "pitch_design_mode_choices": get_pitch_design_mode_choices(),
            "pitch_design_template_choices": design_template_choices,
            "selected_pitch_design_mode": selected_design_mode,
            "selected_pitch_design_template": selected_design_template,
        })

    def post(self, request, submission_id):
        submission = get_object_or_404(IdeaPitchSubmission, id=submission_id)
        if not self._can_access(request, submission):
            return redirect("dashboard")

        action = request.POST.get("action", "generate").strip().lower()
        if action != "generate":
            return redirect("idea_pitch_detail", submission_id=submission.id)

        try:
            pitch_payload = generate_pitch_from_idea(self._to_payload(submission), model_source=submission.model_source)
            submission.generated_pitch = pitch_payload
            submission.status = "generated"
            submission.generated_at = timezone.now()
            submission.save(update_fields=["generated_pitch", "status", "generated_at", "updated_at"])
            messages.success(request, "Pitch completo gerado com sucesso. Já está pronto para apresentação.")
        except Exception as exc:
            logger.error("Falha ao gerar pitch completo: %s", str(exc), exc_info=True)
            messages.error(request, "Não foi possível gerar o pitch completo. Tente novamente.")

        return redirect("idea_pitch_detail", submission_id=submission.id)


class PublicIdeasView(RoleRequiredMixin, View):
    allowed_roles = {ROLE_PUBLICO}

    @staticmethod
    def _ranking_points(submission) -> float:
        avg_stars = float(getattr(submission, "avg_stars", 0) or 0)
        endorsements = int(getattr(submission, "endorsement_count", 0) or 0)
        feedbacks = int(getattr(submission, "feedback_count", 0) or 0)
        return round((avg_stars * 18.0) + (endorsements * 4.0) + (feedbacks * 2.0), 2)

    def get(self, request):
        query = (request.GET.get("q") or "").strip()
        submissions_qs = IdeaPitchSubmission.objects.all()
        if query:
            submissions_qs = submissions_qs.filter(
                Q(startup_name__icontains=query)
                | Q(one_liner__icontains=query)
                | Q(problem__icontains=query)
                | Q(solution__icontains=query)
                | Q(target_customer__icontains=query)
            )

        submissions_qs = submissions_qs.annotate(
            avg_stars=Avg("public_feedbacks__stars"),
            feedback_count=Count("public_feedbacks", distinct=True),
            endorsement_count=Count("public_feedbacks", filter=Q(public_feedbacks__endorsed=True), distinct=True),
            comments_count=Count(
                "public_feedbacks",
                filter=(~Q(public_feedbacks__comment="") & ~Q(public_feedbacks__comment__isnull=True)),
                distinct=True,
            ),
        )

        submissions = list(submissions_qs)
        for submission in submissions:
            submission.ranking_points = self._ranking_points(submission)

        submissions.sort(
            key=lambda item: (
                item.ranking_points,
                float(getattr(item, "avg_stars", 0) or 0),
                int(getattr(item, "endorsement_count", 0) or 0),
                item.created_at,
            ),
            reverse=True,
        )
        for idx, submission in enumerate(submissions, start=1):
            submission.rank_position = idx

        my_feedback_by_submission = {}
        if submissions and request.user.is_authenticated:
            submission_ids = [item.id for item in submissions]
            my_feedbacks = IdeaPublicFeedback.objects.filter(
                user=request.user,
                submission_id__in=submission_ids,
            ).values("submission_id", "stars", "endorsed")
            my_feedback_by_submission = {
                row["submission_id"]: {"stars": row["stars"], "endorsed": row["endorsed"]}
                for row in my_feedbacks
            }
            for submission in submissions:
                submission.my_feedback = my_feedback_by_submission.get(submission.id)

        return render(request, "analyzer/public_ideas.html", {
            "ideas": submissions,
            "search_query": query,
            "total_ideas": len(submissions),
        })


class PublicIdeaDetailView(RoleRequiredMixin, View):
    allowed_roles = {ROLE_PUBLICO}

    def get(self, request, submission_id):
        submission = get_object_or_404(IdeaPitchSubmission, id=submission_id)
        feedback_qs = IdeaPublicFeedback.objects.filter(submission=submission).select_related("user")

        stats = feedback_qs.aggregate(
            avg_stars=Avg("stars"),
            feedback_count=Count("id"),
            endorsement_count=Count("id", filter=Q(endorsed=True)),
            comments_count=Count("id", filter=(~Q(comment="") & ~Q(comment__isnull=True))),
        )
        my_feedback = feedback_qs.filter(user=request.user).first() if request.user.is_authenticated else None
        comments = feedback_qs.exclude(comment="").order_by("-updated_at")

        return render(request, "analyzer/public_idea_detail.html", {
            "submission": submission,
            "stats": stats,
            "my_feedback": my_feedback,
            "comments": comments,
        })


class PublicIdeaFeedbackView(RoleRequiredMixin, View):
    allowed_roles = {ROLE_PUBLICO}

    def post(self, request, submission_id):
        submission = get_object_or_404(IdeaPitchSubmission, id=submission_id)

        stars_raw = (request.POST.get("stars") or "").strip()
        comment = (request.POST.get("comment") or "").strip()
        endorsed = (request.POST.get("endorsed") or "").strip().lower() in {"1", "true", "on", "yes"}

        try:
            stars = int(stars_raw)
        except (TypeError, ValueError):
            messages.error(request, "Selecione uma nota válida entre 1 e 5 estrelas.")
            return redirect("public_idea_detail", submission_id=submission.id)

        if stars < 1 or stars > 5:
            messages.error(request, "A nota deve estar entre 1 e 5 estrelas.")
            return redirect("public_idea_detail", submission_id=submission.id)

        if len(comment) > 2000:
            comment = comment[:2000]

        feedback, created = IdeaPublicFeedback.objects.update_or_create(
            submission=submission,
            user=request.user,
            defaults={"stars": stars, "comment": comment, "endorsed": endorsed},
        )

        if created:
            messages.success(request, "Obrigado! O seu feedback foi registado.")
        else:
            messages.success(request, "O seu feedback foi atualizado com sucesso.")

        return redirect("public_idea_detail", submission_id=submission.id)


class IdeaPitchPDFView(RoleRequiredMixin, View):
    allowed_roles = {ROLE_EMPREENDEDOR, ROLE_ANALISTA, ROLE_ADMIN}

    def get(self, request, submission_id):
        submission = get_object_or_404(IdeaPitchSubmission, id=submission_id)
        if (
            get_user_role(request.user) != ROLE_ADMIN
            and submission.user_id
            and request.user.is_authenticated
            and submission.user_id != request.user.id
        ):
            return redirect("dashboard")
        if submission.user_id and not request.user.is_authenticated:
            return redirect("login")

        if submission.status != "generated" or not submission.generated_pitch:
            payload = {
                "startup_name": submission.startup_name,
                "one_liner": submission.one_liner,
                "problem": submission.problem,
                "solution": submission.solution,
                "target_customer": submission.target_customer,
                "market_size": submission.market_size,
                "business_model": submission.business_model,
                "competitive_advantage": submission.competitive_advantage,
                "traction": submission.traction,
                "team": submission.team,
                "funding_goal": submission.funding_goal,
                "use_of_funds": submission.use_of_funds,
                "call_to_action": submission.call_to_action,
            }
            generated = generate_pitch_from_idea(payload, model_source=submission.model_source)
            submission.generated_pitch = generated
            submission.status = "generated"
            submission.generated_at = timezone.now()
            submission.save(update_fields=["generated_pitch", "status", "generated_at", "updated_at"])

        media_root = settings.MEDIA_ROOT
        try:
            os.makedirs(media_root, exist_ok=True)
        except OSError:
            media_root = os.path.join(settings.BASE_DIR, "media")
            os.makedirs(media_root, exist_ok=True)

        target_dir = os.path.join(media_root, "idea_pitches")
        os.makedirs(target_dir, exist_ok=True)
        safe_name = "".join(ch if ch.isalnum() else "_" for ch in submission.startup_name).strip("_").lower() or "startup"
        output_path = os.path.join(target_dir, f"pitch_{safe_name}_{submission.id}.pdf")

        design_mode, design_template = _resolve_pitch_design_selection(
            request, default_mode=PITCH_DESIGN_MODE_AUTO, default_template="orbit"
        )
        export_pitch_pdf(submission.generated_pitch, output_path, design_mode=design_mode, manual_template=design_template)

        return FileResponse(
            open(output_path, "rb"),
            as_attachment=True,
            filename=f"pitch_completo_{safe_name}.pdf",
            content_type="application/pdf",
        )
