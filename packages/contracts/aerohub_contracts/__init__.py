"""Puertos declarados entre modulos (SRS §2.3 — tabla de dependencias entre modulos).

Ningun modulo de services/ importa el domain/ ni el application/ de otro
modulo (ADR-017 §5.4). Cuando M4 necesita ETA y puerta asignada de M1/M3,
la dependencia se expresa aqui como evento o DTO, nunca como import directo.

Este paquete empieza vacio por diseno: cada evento/puerto se agrega en el
sprint que lo requiere (Fase 1 en adelante), no de forma anticipada.
"""
