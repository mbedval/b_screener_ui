# Remote PostgreSQL Server Setup Guide

To allow the frontend/backend application to connect to your remote PostgreSQL server (e.g., at IP `192.168.1.14`), you must perform the following configuration steps on that remote database server.

---

## 1. Configure PostgreSQL to Listen on All Interfaces

By default, PostgreSQL only listens on `localhost` (`127.0.0.1`), which prevents remote machines from connecting.

1. Locate the `postgresql.conf` file on your remote server.
   * On Debian/Ubuntu: `/etc/postgresql/<version>/main/postgresql.conf`
   * On RHEL/CentOS: `/var/lib/pgsql/<version>/data/postgresql.conf`
2. Open the file and look for the `listen_addresses` directive. Uncomment it and change it to listen on all interfaces:
   ```ini
   listen_addresses = '*'
   ```

---

## 2. Configure Host-Based Authentication (pg_hba.conf)

You must tell PostgreSQL to accept connections from your client machine's IP address or the subnet where it resides.

1. Locate the `pg_hba.conf` file in the same directory as `postgresql.conf`.
2. Add a line at the end of the file to allow access. 

   * **Option A: Allow your specific client IP (Most secure)**
     ```text
     # TYPE  DATABASE        USER            ADDRESS                 METHOD
     host    all             all             192.168.1.XX/32         scram-sha-256
     ```
     *(Replace `192.168.1.XX` with the IP address of the machine running the frontend/backend).*

   * **Option B: Allow the entire local subnet**
     ```text
     # TYPE  DATABASE        USER            ADDRESS                 METHOD
     host    all             all             192.168.1.0/24          scram-sha-256
     ```

> [!NOTE]
> We recommend using `scram-sha-256` (or `md5`) authentication method. Avoid using `trust` for remote connections, as it disables password verification.

---

## 3. Configure the System Firewall

The remote server's OS firewall must allow incoming connections on PostgreSQL's default port (`5432`).

### For UFW (Ubuntu / Debian)
Allow incoming PostgreSQL traffic from any IP:
```bash
sudo ufw allow 5432/tcp
```
Or allow only from your specific client IP:
```bash
sudo ufw allow from 192.168.1.XX to any port 5432 proto tcp
```

### For Firewalld (RHEL / CentOS / Rocky Linux)
```bash
sudo firewall-cmd --add-port=5432/tcp --permanent
sudo firewall-cmd --reload
```

---

## 4. Restart PostgreSQL Service

Apply the configuration changes by restarting PostgreSQL:
```bash
sudo systemctl restart postgresql
```

---

## 5. Verify the Connection

From the client machine (where this dashboard runs), you can test network connectivity to the remote port:
```bash
nc -zv 192.168.1.14 5432
```
Or test database connection directly using `psql` if installed:
```bash
psql -h 192.168.1.14 -U jmbx -d bsa_db
```
