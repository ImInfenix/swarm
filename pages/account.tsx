import { useSession } from "next-auth/react"

export default function Account() {

    const { data: session, status } = useSession()

    return (
        <div>
            <h1>Account</h1>
            <p>
                This is the account page for {session?.user?.name}
            </p>
        </div>
    )
}