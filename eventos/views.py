from django.shortcuts import render,redirect, get_object_or_404
from django.http import HttpResponse,Http404
from django.contrib.auth.decorators import login_required
from .models import Evento,Certificado
from django.urls import reverse
from django.contrib import messages
from django.contrib.messages import constants
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import csv
from secrets import token_urlsafe
import os
import sys
from django.conf import settings
from PIL import Image,ImageDraw,ImageFont

@login_required
def novo_evento(request):
    if request.method == "GET":
        return render(request,'novo_evento.html')
    elif request.method == "POST":
        nome = request.POST.get('nome')
        descricao = request.POST.get('descricao')
        data_inicio = request.POST.get('data_inicio')
        data_termino = request.POST.get('data_termino')
        carga_horaria = request.POST.get('carga_horaria')

        cor_principal = request.POST.get('cor_principal')
        cor_secundaria = request.POST.get('cor_secundaria')
        cor_fundo = request.POST.get('cor_fundo')
        
        logo = request.FILES.get('logo')

        evento = Evento(
            criador=request.user,
            nome=nome,
            descricao=descricao,
            data_inicio=data_inicio,
            data_termino=data_termino,
            carga_horaria=carga_horaria,
            cor_principal=cor_principal,
            cor_secundaria=cor_secundaria,
            cor_fundo=cor_fundo,
            logo=logo,
        )

        evento.save()

        messages.add_message(request,constants.SUCCESS, 'Evento cadastrado com sucesso')
        return redirect(reverse('novo_evento'))
    
@login_required
def gerenciar_evento(request):
    if request.method == "GET":
        eventos = Evento.objects.filter(criador=request.user)
        nome = request.GET.get('nome')
        if nome:
            eventos = eventos.filter(nome__contains=nome)
        return render(request,'gerenciar_evento.html',{'eventos':eventos})
    
@login_required(login_url='/usuario/login/')
def inscrever_evento(request,id):
    evento = get_object_or_404(Evento, id=id)

    if request.method == "GET":
        return render(request,'inscrever_evento.html', {'evento' : evento})
    
    elif request.method == "POST":
        user_is_participante = evento.participantes.filter(id=request.user.id).exists()
        if user_is_participante:
            messages.warning(request, 'Voce já é participante')
            return redirect(reverse('inscrever_evento',kwargs={'id': id}))
        
        evento.participantes.add(request.user)
        evento.save()
        messages.add_message(request, constants.SUCCESS, 'Inscriçao realizada com sucesso')
        return redirect(reverse('inscrever_evento',kwargs={'id': id}))
    
def participante_evento(request,id):
    evento = get_object_or_404(Evento, id=id)
    if not evento.criador == request.user:
        raise Http404('esse evento n é seu')
    if request.method == "GET":
        participantes = evento.participantes.all()[0:3]
        return render(request,'participantes_evento.html', {'participantes':participantes,'evento':evento})
    
def gerar_csv(request,id):
    evento = get_object_or_404(Evento, id=id)
    if not evento.criador == request.user:
        raise Http404('esse evento não é seu')
    
    participantes = evento.participantes.all()

    token = f'{token_urlsafe(6)}'

    path = os.path.join(settings.MEDIA_ROOT, token)

    with open(path,'w') as arq:
        writer = csv.writer(arq, delimiter=',')
        for participante in participantes:
            x = (participante.username, participante.email)
            writer.writerow(x)
    return redirect(f'/media/{token}')

def certificados_evento(request, id):
    evento = get_object_or_404(Evento, id=id)
    if not evento.criador == request.user:
        raise Http404('esse evento não é seu') #o TODO de certificado aqui
    
    if request.method == "GET":
        qtd_certificados = evento.participantes.all().count() - Certificado.objects.filter(evento=evento).count()
        return render(request,'certificados_eventos.html', {'qtd_certificados' : qtd_certificados, 'evento': evento})
  
def gerar_certificado (request, id):
    evento = get_object_or_404(Evento, id=id)
    if not evento.criador == request.user:
        raise Http404('Esse evento não é seu')

    path_template = os.path.join(settings.BASE_DIR, 'templates/static/evento/img/template_certificado.png')
    path_fonte = os.path.join(settings.BASE_DIR, 'templates/static/fontes/arimo.ttf')
    for participante in evento.participantes.all():
        # TODO: Validar se já existe certificado desse participante para esse evento
        img = Image.open(path_template)
        draw = ImageDraw.Draw(img)
        fonte_nome = ImageFont.truetype(path_fonte, 60)
        fonte_info = ImageFont.truetype(path_fonte, 30)
        draw.text((230, 651), f"{participante.username}", font=fonte_nome, fill=(0, 0, 0))
        draw.text((761, 782), f"{evento.nome}", font=fonte_info, fill=(0, 0, 0))
        draw.text((816, 849), f"{evento.carga_horaria} horas", font=fonte_info, fill=(0, 0, 0))

        output = BytesIO()
        img.save(output, format="PNG", quality=100)
        output.seek(0)
        
        img_final = InMemoryUploadedFile(output,
                                        'ImageField',
                                        f'{token_urlsafe(8)}.png',
                                        'image/jpeg',
                                        sys.getsizeof(output),
                                        None)
        
        certificado_gerado = Certificado(
            certificado=img_final,
            participantes=participante,
            evento=evento
        )

        certificado_gerado.save()
    
    messages.add_message(request, constants.SUCCESS, 'Certificados gerados com sucesso')
    return redirect(reverse('certificados_evento', kwargs={'id': evento.id}))

def procurar_certificado(request,id):
    evento = get_object_or_404(Evento, id=id)
    if not evento.criador == request.user:
        raise Http404('Esse evento não é seu')
    
    email = request.POST.get('email')

    certificado = Certificado.objects.filter(evento=evento).filter(participantes__email=email).first()

    if not certificado:
        messages.add_message(request, constants.ERROR, 'esse certificados nao foi gerado')
        return redirect(reverse('certificados_evento', kwargs={'id': evento.id}))

    return redirect(certificado.certificado.url)