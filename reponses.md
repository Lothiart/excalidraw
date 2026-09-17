# TD DORA --- Excalidraw

**Fork GitHub :** https://github.com/Lothiart/excalidraw

## Phase 0 --- Contrat de définitions

Le contrat de définitions utilisé pour le TD est repris à la fin du
fichier.

------------------------------------------------------------------------

## Phase 1 --- Reconnaissance

### 1. Environnements trouvés

J'ai trouvé six environnements différents :

-   `Production – excalidraw`
-   `Production – excalidraw-package-example`
-   `Production – excalidraw-package-example-with-nextjs`
-   `Preview – excalidraw`
-   `Preview – excalidraw-package-example`
-   `Preview – excalidraw-package-example-with-nextjs`

### 2. Environnement à retenir

Pour les métriques DORA, je retiens uniquement
`Production – excalidraw`, puisque c'est l'environnement de production
de l'application étudiée.

J'exclus les trois environnements `Preview`, qui correspondent à de la
préproduction, ainsi que les deux environnements `Production` liés aux
exemples de packages, car ils ne concernent pas directement
l'application Excalidraw.

### 3. Surestimation de la deployment frequency

Dans les données observées, il y avait 90 déploiements
`Preview – excalidraw` et 2 déploiements `Production – excalidraw`.

Si les previews étaient comptées avec la production, cela donnerait 92
déploiements au lieu de 2 :

`92 / 2 = 46`

La deployment frequency serait donc surestimée d'un facteur **46**.

### 4. Erreur correspondante dans le support

Cela correspond à l'erreur du chapitre 7.3 qui consiste à **compter les
builds comme des déploiements**. Il faut filtrer les événements pour ne
garder que les vrais déploiements de production de l'application.

### 5. Statut d'un déploiement

Sur le dernier déploiement `Production – excalidraw` observé, le tableau
des statuts contient un statut `success`.

La simple présence d'un Deployment ne prouve donc pas qu'un changement
est bien arrivé en production. Il faut aussi vérifier qu'il possède un
statut indiquant que le déploiement a réussi.

### 6. Horodatage retenu

Sur le déploiement observé, le `created_at` du Deployment et celui du
statut `success` sont identiques :

`2026-09-16T20:00:59Z`

Dans notre contrat, nous avions choisi de retenir le `created_at` du
statut `success`, car il correspond au moment où le déploiement est
considéré comme réussi.

------------------------------------------------------------------------

## Phase 2 --- Collecte outillée

### Résultats

  Métrique                                                         Valeur
  -------------------------------------- --------------------------------
  Deployment frequency                     0,178 / jour (16 déploiements)
  Délai médian entre deux déploiements                          4,0 jours
  Change lead time P50                                             42,5 h
  Change lead time P90                                          8,5 jours
  Commits / lots                                     76 commits / 15 lots

### 7. Taille moyenne des lots

Le collecteur a analysé 76 commits répartis dans 15 lots.

`76 / 15 ≈ 5,1`

On obtient donc une moyenne d'environ **5,1 commits par lot**. Le
chapitre 6.1 explique que travailler avec de petits lots est
intéressant, car cela permet de réduire la taille des changements et
facilite leur livraison.

### 8. Écart entre P50 et P90

Le P50 est de 42,5 heures, soit environ 1,77 jour, alors que le P90 est
de 8,5 jours.

`8,5 / 1,77 ≈ 4,8`

Le P90 est donc environ **4,8 fois plus élevé que le P50**. Cet écart
montre qu'il existe une longue traîne : certains changements prennent
beaucoup plus de temps que le changement habituel. En revanche, cela ne
veut pas dire que tous les changements sont lents.

### 9. Deployment frequency et distribution 2024

Nous avons obtenu une fréquence de **0,178 déploiement par jour**, soit
16 déploiements sur 90 jours. Le délai médian entre deux déploiements
est de 4 jours.

Cette valeur permet de situer grossièrement le rythme de déploiement par
rapport à la distribution 2024, mais il faut rester prudent. Comme
l'explique le chapitre 4.1, les groupes observés dans l'étude servent
surtout de repères et ne sont pas des seuils fixes permettant de classer
directement une équipe.

### 10. Pourquoi utiliser le délai médian ?

Pour une équipe qui déploie peu, dire qu'elle déploie typiquement tous
les 4 jours est plus parlant qu'une fréquence de `0,178 / jour`.

La médiane donne directement une idée du rythme habituel entre deux
déploiements et évite qu'une fréquence brute soit difficile à
interpréter.

### 11. Les trois métriques en `n/a`

Les trois métriques qui restent en `n/a` sont :

-   Failed Deployment Recovery Time ;
-   Change Fail Rate ;
-   Deployment Rework Rate.

Elles ont toutes besoin d'informations supplémentaires que les données
de déploiement ne donnent pas directement. Il faut notamment savoir
quels incidents sont liés à quels déploiements et quels déploiements
correspondent à du rework.

### 12. Le maillon faible

Le maillon faible présenté au chapitre 5.1 est le lien entre
**l'incident et le déploiement qui l'a causé**.

Les données publiques permettent de voir les commits, les déploiements
et les issues, mais elles ne permettent pas de savoir de manière fiable
quel déploiement précis a provoqué un incident. Si ce lien n'a jamais
été enregistré, le collecteur ne peut pas le deviner.

### 13. Limite de la règle des 24 heures

La règle « un nouveau déploiement dans les 24 heures signifie que le
précédent a échoué » peut se tromper dans les deux sens.

Un **faux positif** serait par exemple un second déploiement prévu
normalement quelques heures après le premier. Il ne s'agit pas forcément
d'une correction.

Un **faux négatif** serait un incident réellement provoqué par un
déploiement, mais dont la correction ou le rollback arrive plus de 24
heures plus tard.

------------------------------------------------------------------------

## Phase 3 --- Le proxy et ses limites

### 14. Issues `bug`

Sur la fenêtre de 90 jours, le collecteur trouve **23 issues avec le
label `bug`**.

Parmi ces 23 issues, **aucune n'est rattachée à un déploiement**.

### 15. Vérification dans GitHub

Dans l'interface GitHub, nous avons obtenu :

-   **140 issues** toutes catégories sur les 90 derniers jours : 122
    ouvertes et 18 fermées ;
-   **765 issues `bug`** depuis la création du dépôt : 211 ouvertes et
    554 fermées.

### 16. Comparaison des résultats

Les trois nombres ne correspondent pas exactement au même périmètre.

Le collecteur trouve 23 issues `bug` sur les 90 derniers jours. Sur la
même période, 140 issues ont été ouvertes toutes catégories confondues.
Enfin, les 765 issues `bug` correspondent à tout l'historique du dépôt.

On voit donc que le label `bug` existe beaucoup dans l'historique du
projet, mais qu'il n'est présent que sur une partie des issues récentes.
Surtout, aucune des 23 issues trouvées par le collecteur n'est reliée à
un déploiement.

### 17. Une quatrième explication au taux de 0 %

Dans notre cas, une autre explication est que **le proxy utilisé ne
correspond pas forcément à ce que l'on cherche réellement à mesurer**.

Une issue marquée `bug` n'est pas forcément un incident de production
causé par un déploiement. Utiliser uniquement ce label ne permet donc
pas de calculer correctement le Change Fail Rate.

### 18. Métrique sensible à la saisie

Le support indique que le **Deployment Rework Rate** est
particulièrement sensible à la discipline de saisie.

Ce n'est pas un hasard : pour identifier le rework, il faut disposer
d'un marqueur fiable, par exemple une branche commençant par `hotfix/`.
Si ce marqueur n'est pas renseigné ou n'est pas conservé dans les
données du déploiement, l'outil ne peut pas reconnaître correctement le
rework.

------------------------------------------------------------------------

## Phase 4 --- Produire la donnée manquante

### Résultats sur le fork

Après avoir ajouté le workflow de déploiement, créé les déploiements et
simulé un incident, le collecteur donne :

``` text
DÉBIT
  Deployment frequency                 0.089 /jour  (8 déploiements)
    délai médian entre deux            0.0 h
  Change lead time (P50)               0.0 h
  Change lead time (P90)               0.0 h
    base de calcul                     3 commits / 3 lots
  Failed deployment recovery time      0.2 h

INSTABILITÉ
  Change fail rate                     12.5 %
  Deployment rework rate               0.0 %

INCIDENTS
  Issues "incident"                    1
    rattachées à un déploiement        1
```

### 19. Ce que l'on peut maintenant calculer

Cette fois, le **Change Fail Rate** et le **Failed Deployment Recovery
Time** sont calculables.

Le collecteur obtient :

-   Change Fail Rate : **12,5 %**
-   Failed Deployment Recovery Time : **0,2 h**

C'est possible parce que l'incident que nous avons créé est
explicitement relié à son déploiement avec le champ `caused_by`.

Le Deployment Rework Rate donne également une valeur numérique de **0,0
%**. Cette valeur ne reflète cependant pas le hotfix que nous avons
réalisé : dans les données observées, le déploiement du hotfix est
enregistré avec le SHA du commit et pas avec une référence commençant
par `hotfix/`.

### 20. Temps passé à produire la donnée

Nous avons passé environ **45 minutes en phase 3** à essayer de
retrouver ou de déduire les informations manquantes à partir des données
existantes.

En phase 4, il nous a fallu environ **30 minutes** pour produire
directement la donnée manquante sur le fork.

Dans notre cas, produire correctement l'information à la source a donc
été plus rapide que d'essayer de la reconstruire après coup.

### 21. Le Change Fail Rate est-il représentatif ?

Non. Le Change Fail Rate obtenu est de **12,5 %**, mais il repose
seulement sur **8 déploiements et un incident simulé**.

Il faudrait davantage de données, sur une période plus longue et avec de
vrais déploiements de production. Il faudrait aussi enregistrer
systématiquement les incidents et les rattacher au déploiement
responsable pour obtenir une mesure plus représentative.

------------------------------------------------------------------------

## Phase 5 --- Lecture critique des outils

### 22. Un outil professionnel changerait-il le résultat ?

Non. Avec les seules données publiques disponibles sur Excalidraw, un
outil professionnel rencontrerait le même problème que notre collecteur
pour calculer correctement le Change Fail Rate.

Il lui manquerait le lien entre les incidents et les déploiements qui
les ont causés. C'est précisément l'information qui manquait en phase 2.

Le problème ne vient donc pas du fait que notre collecteur est un petit
script : même un outil plus complet ne peut pas reconstruire de façon
fiable une donnée qui n'a jamais été enregistrée.

### 23. Pourquoi l'outillage arrive-t-il en dernier ?

Pendant le TD, on a vu que disposer d'un outil ne suffit pas. Avant de
collecter des métriques, il faut savoir ce que l'on veut mesurer et
définir clairement les conventions utilisées.

Par exemple, il a fallu décider quel environnement correspond à la
production et comprendre comment relier un incident à un déploiement.

L'ordre Quick Check, conversation, puis instrumentation est donc logique
: on commence par comprendre ce que l'on cherche à mesurer, puis on
ajoute seulement l'instrumentation dont on a réellement besoin.

### 24. Vérifier un outil avant de l'adopter

Avant d'utiliser un outil trouvé dans un tutoriel, il faut vérifier
qu'il est encore maintenu.

Four Keys en est un bon exemple : il a longtemps été cité comme
référence, mais le projet est maintenant archivé. Il faut donc regarder
l'état du dépôt, la date des dernières versions et l'activité récente du
projet plutôt que de se fier uniquement à un tutoriel qui peut être
ancien.

------------------------------------------------------------------------

## Contrat de définitions

Contenu de `dora-definitions.yml` :

``` yaml
application: excalidraw

deploiement:
  compte_comme_deploiement: "Deployment Status 'success' sur l'environnement 'Production – excalidraw'"
  exclut:
    - "Preview – excalidraw"
    - "Preview – excalidraw-package-example"
    - "Preview – excalidraw-package-example-with-nextjs"
    - "Production – excalidraw-package-example"
    - "Production – excalidraw-package-example-with-nextjs"
  horodatage: "created_at du Deployment Status 'success'"

changement:
  point_de_depart: "committer date du commit sur la branche par défaut"

incident:
  definition: "dégradation en production nécessitant une intervention"
  source: "issue GitHub portant le label 'incident'"
  debut: "horodatage de détection de l'incident"
  fin: "moment où le service est rétabli"
  rattachement_deploiement: "champ 'caused_by' contenant l'identifiant du déploiement responsable"

rework:
  marqueur: "branche dont le nom commence par hotfix/"

fenetre_de_reference: "90 jours glissants"
agregation: "médiane pour les durées, P90 publié en complément"
```
