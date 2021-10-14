import { Flex, Center } from '@chakra-ui/layout'
import React, { Component } from 'react'
import Form from './Form.js'

export class login extends Component {
    render() {
        return (
            <div>
                <div position="relative" justifyContent="center">
                    <Flex direction="column">
                        <Form value="Login"/>
                    </Flex>
                </div>
            </div>
        )
    }
}

export default login
