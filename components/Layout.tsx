import Head from 'next/head'
import TopBar from './TopBar'

type Props = {
  children?: React.ReactNode
}

export default function Layout({ children }: Props) {
  return (
    <>
      <Head>
        <title>Swarm</title>
        <meta name="description" content="A community oriented bug tracker" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <TopBar />
      <main>{children}</main>
    </>
  )
}
