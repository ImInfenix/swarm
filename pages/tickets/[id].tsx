import { GetServerSidePropsContext, InferGetServerSidePropsType } from 'next'
import Head from 'next/head'
import { Prisma } from '@prisma/client'
import prismaInstance from '../../lib/prisma'

export default function TicketLayout(props: InferGetServerSidePropsType<typeof getServerSideProps>) {
  if (props.ticket === undefined || props.ticket === null) {
    return null
  }

  return (
    <>
      <Head>
        <title>{props.ticket.title}</title>
      </Head>

      <h1>Hello {props.ticket.id}</h1>
      <p>Received data is {props.ticket.id}</p>

      <h3>{props.ticket.title}</h3>
      <p>{props.ticket.content}</p>
    </>
  )
}

export async function getServerSideProps(context: GetServerSidePropsContext) {
  if (typeof context?.params?.id !== 'string') {
    return { props: {} }
  }

  const idStr: string = context?.params?.id

  if (idStr === undefined) {
    return { props: {} }
  }

  const id: number = parseInt(idStr)
  var ticket: Prisma.PromiseReturnType<typeof prismaInstance.ticket.findUnique> =
    await prismaInstance.ticket.findUnique({
      where: {
        id: id,
      },
    })

  ticket = JSON.parse(JSON.stringify(ticket))

  return { props: { ticket } }
}
