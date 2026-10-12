# Architecture de Swarm

Ce document décrit la version de Swarm à construire. Le prototype de 2022, conservé sur la branche `prototype_2022`, utilise Next.js, React, Prisma et PostgreSQL ; ces éléments ne font pas partie de l'architecture retenue ci-dessous.

## 1. Technologies retenues et raisons

### Application : Python et Django 5.2

Django fournit dans une seule application le routage, le rendu des pages, les formulaires, la validation, la gestion des comptes, les permissions, l'accès aux données et les migrations. Cette intégration limite le nombre de composants à assembler et à maintenir pour un outil principalement fondé sur des listes, des formulaires et des échanges entre utilisateurs.

La série 5.2 est compatible avec Python 3.10, déjà installé dans l'environnement de développement. Les dépendances seront fixées à des versions précises pour rendre l'installation reproductible.

### Données : SQLite

SQLite conserve les données dans un fichier local. Une instance de Swarm sur un seul serveur peut ainsi fonctionner sans service de base de données supplémentaire, ce qui simplifie le développement, l'installation et l'auto-hébergement.

Le fichier sera placé dans un emplacement persistant, hors des fichiers remplacés lors d'un déploiement. Les sauvegardes devront produire une copie cohérente d'une base en cours d'utilisation et une restauration devra être testée. Le fichier ne sera pas partagé entre plusieurs serveurs au moyen d'un système de fichiers réseau.

Le modèle de données utilisera autant que possible les fonctions communes de l'ORM de Django. Un passage ultérieur à PostgreSQL restera ainsi une migration du schéma, des données et du déploiement, sans exiger une réécriture de l'application. SQLite reste le choix initial tant que la charge et les besoins de concurrence le permettent.

### Interface : templates Django, HTML, CSS et JavaScript natif

Les pages seront rendues par le serveur. Le CSS définira une interface responsive et accessible ; JavaScript sera réservé aux interactions qui améliorent réellement l'usage. Aucune bibliothèque frontend n'est requise pour la première version. Cette approche évite une seconde application, une API interne systématique et une chaîne de compilation JavaScript.

Une bibliothèque légère pourra être ajoutée plus tard pour une interaction précise si le besoin apparaît. React et Next.js ne sont pas retenus pour cette version.

L'interface utilise les traductions intégrées à Django. L'anglais est la langue par défaut et le français reste disponible. La préférence d'un membre est enregistrée avec son compte ; celle d'un visiteur est conservée dans un cookie.

### API externe : Django REST Framework

Une API JSON versionnée couvre les comptes, les projets, les tickets et les commentaires. Django REST Framework apporte la validation des requêtes, les réponses JSON, la pagination et les contrôles d'accès sans créer une seconde application ni dupliquer le modèle de données. Les pages HTML et l'API partagent les mêmes règles métier.

Les clients externes utilisent un jeton Bearer révocable, valable 30 jours. Seul son condensat SHA-256 est conservé en base ; le jeton brut n'est remis qu'à sa création. Les lectures publiques restent accessibles sans jeton. Les clients doivent utiliser HTTPS en production. Les appels depuis un autre site web ne sont pas autorisés par CORS dans la configuration initiale.

### Comptes et sécurité : fonctions intégrées à Django

L'authentification par compte et mot de passe, les sessions, la protection contre les requêtes intersites et les contrôles d'accès s'appuieront sur Django. Les clients de l'API utilisent des jetons distincts des sessions du site. Chaque opération sensible vérifiera les droits côté serveur. Une connexion par un fournisseur externe pourra être étudiée après la première version, sans être nécessaire à son fonctionnement.

### Exploitation et vérification

Le déploiement visé est une instance unique de l'application derrière un serveur HTTPS, avec un emplacement persistant pour SQLite et les éventuels fichiers déposés par les utilisateurs. Les migrations seront exécutées explicitement lors des mises à jour. Les parcours essentiels et les règles de permissions seront vérifiés par les outils de test de Django.

La base PostgreSQL du prototype restera distincte tant qu'une reprise de ses données n'aura pas été décidée et vérifiée. Aucun secret ne doit être versionné dans le dépôt. Les anciens fichiers d'environnement locaux ont été supprimés ; les éventuelles valeurs réelles qu'ils contenaient doivent être renouvelées avant toute mise en service.

## 2. Concept de l'application

Swarm est un espace de suivi de problèmes organisé par projets. Il permet à une communauté de signaler un problème, de suivre son traitement et de discuter d'une solution dans un lieu commun.

### Personnes et accès

- Un visiteur peut consulter les projets, les tickets et leurs discussions.
- Un membre peut créer un projet, ouvrir un ticket et participer aux discussions.
- Le créateur d'un projet en est le responsable : il peut modifier sa présentation et organiser le traitement de ses tickets.
- L'auteur d'un ticket peut corriger sa description. Les changements concernant le traitement du ticket relèvent du responsable du projet.
- Un administrateur peut intervenir sur les comptes et les contenus en cas d'abus ou d'erreur.
- Chacun peut lire l'interface en anglais ou en français. Le choix d'un membre est retrouvé lorsqu'il se reconnecte.

### Projets

Chaque projet possède un nom, une description et un responsable. Sa page rassemble les tickets qui le concernent et donne une vue de leur avancement. Les visiteurs peuvent parcourir la liste des projets et ouvrir la page de chacun.

### Tickets

Un ticket appartient à un projet. Il contient un titre, une description, un auteur, une priorité et un état. Les états prévus sont **ouvert**, **en cours**, **résolu** et **fermé**. Un responsable peut faire évoluer l'état et la priorité ; l'historique des échanges reste visible après la résolution.

Les membres peuvent commenter un ticket pour apporter des précisions ou suivre sa résolution. La date de création et la dernière activité sont visibles afin de replacer les échanges dans leur contexte.

### Parcours de la première version

Un visiteur découvre les projets et les tickets récents, puis peut filtrer les tickets d'un projet selon leur état ou leur priorité. Pour contribuer, il crée un compte et se connecte. Il peut alors ouvrir un ticket dans un projet ou répondre à un ticket existant. Le responsable du projet examine les nouveaux signalements, ajuste leur priorité et fait avancer leur état jusqu'à leur clôture.

La première version se concentre sur ce parcours. Les pièces jointes, les notifications, les votes, les échanges en temps réel et les intégrations externes restent hors de son périmètre initial.

