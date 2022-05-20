import { getSession } from 'next-auth/react'
import TicketsSummary from '../components/TicketsSummary'
import styles from '../styles/Home.module.css'
import { Prisma } from '@prisma/client'
import { GetServerSidePropsContext, InferGetServerSidePropsType } from 'next'
import prisma from '../lib/prisma'

export default function Home(props: InferGetServerSidePropsType<typeof getServerSideProps>) {
  return (
    <div className={styles.container}>
      <div className={styles.main}>
        <h1 className={styles.title}>Welcome to Swarm</h1>

        <p className={styles.description}>A community-oriented bug tracker</p>

        <p>You are currently {props.connectionStatus}</p>

        <TicketsSummary ticketCount={props.ticketCount} />
      </div>
    </div>
  )
}

export async function getServerSideProps(context: GetServerSidePropsContext) {
  const ticketCount: Prisma.PromiseReturnType<typeof prisma.ticket.count> = await prisma.ticket.count()

  const session = await getSession(context)
  const connectionStatus: string = session ? 'connected' : 'disconnected'

  return { props: { ticketCount, connectionStatus } }
}