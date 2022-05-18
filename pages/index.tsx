import type { NextPage } from 'next'
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

        <TicketsSummary ticketCount={props.ticketCount} />
      </div>
    </div>
  )
}


export async function getServerSideProps(context: GetServerSidePropsContext) {
  var ticketCount: Prisma.PromiseReturnType<typeof prisma.ticket.count> = await prisma.ticket.count();
  return { props: { ticketCount } }
} 