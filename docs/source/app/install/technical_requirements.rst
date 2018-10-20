
Technical requirements
======================

The following list specifies the minimum requirements:

1. **Mikrotik router** (1)

    Router specifications:
        * Eight (8) or more Gigabit Ethernet ports.

    A Gigabit Ethernet connection is recommended for optimal use. Resela has been
    tested with the *CCR1016-12G* and *CCR1036-12G-4S* models.

    Paraphernalia:
        * One (1) Ethernet or fiber cable for the Internet connection.
        * Two (2) Ethernet cables for *Controller* connections.
        * Two (2) Ethernet cables per *Compute* node.

2. **Controller node** (1)

    * **OS:** Ubuntu Server 16.04
    * **CPU:** 1 processor
    * **RAM:** 12 GB minimum
    * **Storage:** 64 GB

3. **Compute nodes** (1+)

    * **OS:** Ubuntu Server 16.04
    * **CPU:** 1 processor
    * **RAM:** 100 GB total for the *Compute* nodes
    * **Storage:** 10 GB

.. Note::

    It is possible to add more RAM for the compute nodes
    depending on how many instances the system is meant to handle.