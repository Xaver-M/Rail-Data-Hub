/**
 * server.mjs
 * ==========
 * Lokaler REST-Microservice für DB-Preisdaten.
 * Nutzt db-vendo-client (dbnav-Profil) + hafas-rest-api.
 *
 * Setup (einmalig):
 *   npm install db-vendo-client hafas-rest-api
 *
 * Starten:
 *   node server.mjs
 *
 * Läuft dann auf http://localhost:3123
 * Python-Crawler spricht diesen Port an.
 */

import { createClient }        from 'db-vendo-client'
import { withThrottling }      from 'db-vendo-client/throttle.js'
import { withRetrying }        from 'db-vendo-client/retry.js'
import { profile as dbnavProfile } from 'db-vendo-client/p/db/index.js'
import { createHafasRestApi }  from 'hafas-rest-api'

// ---------------------------------------------------------------------------
// Konfiguration
// ---------------------------------------------------------------------------

const PORT       = process.env.PORT       || 3123
const USER_AGENT = process.env.USER_AGENT || 'rail-data-hub/1.0 (KIT Karlsruhe, github.com/Xaver-M/Rail-Data-Hub)'

// ---------------------------------------------------------------------------
// Client & API erstellen
// ---------------------------------------------------------------------------

const client          = createClient(dbnavProfile, USER_AGENT)
// Throttling: max. 2 Requests/Sekunde um Rate Limits zu vermeiden
const throttledClient = withThrottling(client, 2, 1000)
// Retrying: bei transienten Fehlern automatisch wiederholen
const robustClient    = withRetrying(throttledClient)
// withThrottling/withRetrying leiten .profile nicht weiter — hafas-rest-api braucht es
robustClient.profile  = client.profile

const config = {
    hostname:    'localhost',
    name:        'rail-data-hub-db-microservice',
    homepage:    'https://github.com/Xaver-M/Rail-Data-Hub',
    version:     '1.0.0',
    aboutPage:   false,
    cors:        true,   // Python kann von localhost anfragen
}

const api = await createHafasRestApi(robustClient, config)

api.listen(PORT, (err) => {
    if (err) {
        console.error('Fehler beim Starten:', err)
        process.exit(1)
    }
    console.log(` DB Microservice läuft auf http://localhost:${PORT}`)
    console.log(`   Profil:     dbnav (DB Navigator API)`)
    console.log(`   User-Agent: ${USER_AGENT}`)
    console.log(`   Throttling: 2 req/s`)
    console.log()
    console.log(`   Test:`)
    console.log(`   curl "http://localhost:${PORT}/journeys?from=8002549&to=8000261&departure=2026-05-22T10:00:00&tickets=true"`)
    console.log()
    console.log('   Bereit für Python-Crawler. Mit Ctrl+C beenden.')
})